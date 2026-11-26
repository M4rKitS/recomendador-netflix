"""Motor de recomendación de Netflix basado en contenido.

Cada título se describe con un conjunto de "características" (géneros, director,
reparto, país, clasificación, tipo y palabras clave de la sinopsis). Dos títulos
se parecen cuando comparten características, y compartir una característica rara
(un director concreto) pesa más que compartir una muy común ("Dramas").

Cada título se convierte en un vector (peso del grupo × IDF de cada etiqueta) y la
similitud entre dos títulos es el coseno entre sus vectores.
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from nltk.stem import SnowballStemmer

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

# Peso de cada grupo de características en la puntuación final.
PESOS = {
    "generos": 3.0,
    "temas": 2.0,  # palabras clave de TMDb: "heist", "1980s", "small town"...
    "director": 2.0,
    "reparto": 2.0,
    "palabras_clave": 1.5,
    "pais": 1.0,
    "clasificacion": 0.75,
    "tipo": 0.5,
}

# Solo cuentan los primeros actores del reparto: son los protagonistas.
MAX_ACTORES = 6

# Nombres de columna posibles en los distintos CSV de Netflix de Kaggle.
ALIAS_COLUMNAS = {
    "titulo": ["title"],
    "titulo_original": ["original_title"],
    "titulo_ingles": ["english_title"],
    "temas": ["keywords"],
    "descripcion": ["description"],
    "director": ["director"],
    "generos": ["genres", "listed_in"],
    "reparto": ["cast"],
    "pais": ["production_country", "country"],
    "clasificacion": ["rating"],
    "tipo": ["content_type", "type"],
    "nota": ["tmdb_score", "imdb_score", "vote_average"],
    "votos": ["votes", "vote_count"],
    "estreno": ["release_year", "release_date"],
    "duracion": ["duration"],
    # Solo para la web (descargar_catalogo.py): no intervienen en la recomendación.
    "tmdb_id": ["tmdb_id"],
    "cartel": ["poster"],
    "fondo": ["backdrop"],
}

# Listas mínimas por si no se ha descargado el corpus de stopwords de NLTK.
_STOPWORDS_BASICAS = {
    "english": set(
        "a an the and or but of to in on at for with from by as is are was were be been his "
        "her their its he she they them this that these those who whom which what when where "
        "while into after before about over under up down out new one two must him has have "
        "had not no can will during life".split()
    ),
    "spanish": set(
        "el la los las un una unos unas y o pero de del a al en con por para como es son fue "
        "ser su sus se lo le les que quien cuando donde mientras tras sobre entre hasta desde "
        "este esta estos estas ese esa mas muy sin no nueva nuevo vida".split()
    ),
}


def _cargar_stopwords(idioma):
    try:
        from nltk.corpus import stopwords

        lista = set(stopwords.words(idioma))
    except LookupError:
        lista = set()
    # Sin acentos, igual que el texto una vez normalizado ("está" -> "esta").
    return {normalizar(p) for p in lista | _STOPWORDS_BASICAS[idioma]}


def detectar_idioma(textos, defecto="english"):
    """'spanish' o 'english' según qué palabras vacías abundan más en el texto."""
    muestra = " ".join(str(t) for t in textos[:300] if pd.notna(t)).lower().split()
    espanol = sum(p in {"el", "la", "los", "las", "de", "que", "y", "en", "un", "una"} for p in muestra)
    ingles = sum(p in {"the", "of", "and", "to", "in", "a", "his", "her", "is", "an"} for p in muestra)
    if espanol == ingles:
        return defecto
    return "spanish" if espanol > ingles else "english"


# --------------------------------------------------------------------------- #
# Limpieza de texto
# --------------------------------------------------------------------------- #

def normalizar(texto):
    """Minúsculas, sin acentos y sin signos: 'Pedro Almodóvar' -> 'pedro almodovar'."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def separar_lista(valor):
    """'Drama, Comedia ,  Thriller' -> ['drama', 'comedia', 'thriller']."""
    if pd.isna(valor) or not str(valor).strip():
        return []
    partes = re.split(r"\s*[,;|]\s*", str(valor))
    return [normalizar(p) for p in partes if normalizar(p)]


_PROCESADORES = {}


def palabras_clave(texto, idioma="spanish"):
    """Sinopsis -> raíces de palabras relevantes (sin stopwords) usando NLTK.

    'Unos astronautas luchan por volver' -> ['astronaut', 'luch', 'volv']
    """
    if pd.isna(texto):
        return []
    if idioma not in _PROCESADORES:
        _PROCESADORES[idioma] = (_cargar_stopwords(idioma), SnowballStemmer(idioma))
    stopwords, stemmer = _PROCESADORES[idioma]
    palabras = re.findall(r"[a-z]{3,}", normalizar(texto))
    return [stemmer.stem(p) for p in palabras if p not in stopwords]


def puntuacion(valor):
    """'6.6/10' o 6.6 -> 6.6 (NaN si no hay dato)."""
    coincidencia = re.search(r"\d+(?:\.\d+)?", str(valor))
    return float(coincidencia.group()) if coincidencia else np.nan


# --------------------------------------------------------------------------- #
# Carga del dataset
# --------------------------------------------------------------------------- #

def cargar_dataset(ruta):
    """Lee el CSV y lo deja con columnas en castellano y sin títulos duplicados."""
    df = pd.read_csv(ruta)
    df.columns = [normalizar(c).replace(" ", "_") for c in df.columns]

    columnas = {}
    for nombre, alias in ALIAS_COLUMNAS.items():
        encontrada = next((a for a in alias if a in df.columns), None)
        columnas[nombre] = df[encontrada] if encontrada else pd.Series([np.nan] * len(df))
    datos = pd.DataFrame(columnas)

    if datos["titulo"].isna().all():
        raise ValueError("El CSV no tiene una columna 'title'. ¿Es el dataset de Netflix?")

    datos = datos.dropna(subset=["titulo"])
    datos["titulo"] = datos["titulo"].astype(str).str.strip()
    datos["nota"] = datos["nota"].map(puntuacion)
    datos["votos"] = pd.to_numeric(datos["votos"], errors="coerce")
    datos["tipo"] = datos["tipo"].fillna("Desconocido")
    datos["anio"] = datos["estreno"].astype(str).str.extract(r"(\d{4})", expand=False)

    # Títulos repetidos (remakes, película y serie con el mismo nombre): se distinguen
    # añadiendo el año, "Oldboy (2003)". Si aun así coinciden, son la misma ficha repetida.
    repetidos = datos["titulo"].duplicated(keep=False) & datos["anio"].notna()
    datos.loc[repetidos, "titulo"] = datos["titulo"] + " (" + datos["anio"] + ")"
    return datos.drop_duplicates(subset="titulo").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Motor de recomendación
# --------------------------------------------------------------------------- #

@dataclass
class Recomendacion:
    titulo: str
    tipo: str
    similitud: float  # 0-100
    nota: float
    anio: str
    generos: str
    descripcion: str
    coincidencias: dict = field(default_factory=dict)


class Recomendador:
    def __init__(self, datos, pesos=None, idioma=None):
        self.datos = datos
        self.pesos = pesos or PESOS
        self.idioma = idioma or detectar_idioma(datos["descripcion"].tolist())
        self._indice_titulos = {normalizar(t): i for i, t in enumerate(datos["titulo"])}
        # También se puede buscar por el título original o el inglés:
        # "Money Heist" -> "La casa de papel", "Squid Game" -> "El juego del calamar".
        self._indice_originales = {}
        for columna in ("titulo_original", "titulo_ingles"):
            for i, otro in enumerate(datos[columna]):
                if pd.notna(otro) and normalizar(otro):
                    self._indice_originales.setdefault(normalizar(otro), i)
        self._construir_caracteristicas()

    @classmethod
    def desde_csv(cls, ruta):
        return cls(cargar_dataset(ruta))

    # --- Preparación ------------------------------------------------------- #

    def _etiquetas_de_fila(self, fila):
        """Convierte una fila del dataset en conjuntos de etiquetas por grupo."""
        # Guardamos el texto original de cada etiqueta, por grupo, para mostrarlo en la interfaz
        # (el tema "spain" y el país "Spain" son etiquetas distintas).
        for columna in ("generos", "temas", "director", "reparto", "pais"):
            if pd.notna(fila[columna]):
                for original in re.split(r"\s*[,;|]\s*", str(fila[columna])):
                    self.originales.setdefault((columna, normalizar(original)), original.strip())
        reparto = separar_lista(fila["reparto"])[:MAX_ACTORES]
        return {
            "generos": set(separar_lista(fila["generos"])),
            "director": set(separar_lista(fila["director"])),
            "reparto": set(reparto),
            "pais": set(separar_lista(fila["pais"])),
            "clasificacion": {normalizar(fila["clasificacion"])} if pd.notna(fila["clasificacion"]) else set(),
            "tipo": {normalizar(fila["tipo"])},
            "temas": set(separar_lista(fila["temas"])),
            # Algunas sinopsis están en inglés (TMDb no tenía la traducción): se detecta en cada una.
            "palabras_clave": set(palabras_clave(
                fila["descripcion"], detectar_idioma([fila["descripcion"]], self.idioma)
            )),
        }

    def _construir_caracteristicas(self):
        """Convierte cada título en un vector de características ponderadas.

        Cada característica es una pareja (grupo, etiqueta), p. ej. ("director", "martin scorsese").
        Su valor es  peso del grupo × IDF  : importa más si el grupo pesa más y si la
        etiqueta es rara en el catálogo. Guardamos un índice invertido
        característica -> títulos que la tienen, para comparar muy rápido.
        """
        n = len(self.datos)
        self.originales = {}
        self.etiquetas = [self._etiquetas_de_fila(f) for _, f in self.datos.iterrows()]

        indice = defaultdict(list)
        for i, etiquetas in enumerate(self.etiquetas):
            for grupo in self.pesos:
                for etiqueta in etiquetas[grupo]:
                    indice[(grupo, etiqueta)].append(i)

        # Una etiqueta que solo tiene un título (una palabra rara de su sinopsis, un actor que
        # no sale en nada más) nunca puede coincidir con otro: solo alargaría el vector y
        # rebajaría todas sus afinidades. Se descarta, como el min_df de scikit-learn.
        indice = {clave: ids for clave, ids in indice.items() if len(ids) >= 2}

        # IDF suavizado: cuanto menos títulos comparten una etiqueta, más informa.
        self.idf = {
            clave: np.log((1 + n) / (1 + len(ids))) + 1 for clave, ids in indice.items()
        }
        self.valor = {clave: self.pesos[clave[0]] * idf for clave, idf in self.idf.items()}
        self.indice = {clave: np.array(ids) for clave, ids in indice.items()}

        # Longitud (norma) del vector de cada título, para el coseno, y la de cada grupo por
        # separado, para la afinidad por aspectos.
        self.normas = np.zeros(n)
        self.normas_grupo = {grupo: np.zeros(n) for grupo in self.pesos}
        for i, etiquetas in enumerate(self.etiquetas):
            for grupo in self.pesos:
                self.normas_grupo[grupo][i] = np.sqrt(sum(
                    self.idf.get((grupo, e), 0.0) ** 2 for e in etiquetas[grupo]
                ))
            self.normas[i] = np.sqrt(sum(
                (self.pesos[g] * self.normas_grupo[g][i]) ** 2 for g in self.pesos
            ))
        # Suma de los pesos de los grupos que tiene cada título (sin director, no cuenta).
        self.pesos_presentes = sum(
            np.where(self.normas_grupo[g] > 0, self.pesos[g], 0.0) for g in self.pesos
        )

    # --- Búsqueda de títulos ---------------------------------------------- #

    def buscar_titulos(self, texto, limite=10):
        """Sugerencias para el buscador: primero los que empiezan por el texto.

        Busca en el título del catálogo y en el original, pero siempre devuelve el del catálogo.
        """
        consulta = normalizar(texto)
        if not consulta:
            return []
        patron = re.compile(r"\b" + re.escape(consulta))
        empiezan, contienen = {}, {}
        for indice in (self._indice_titulos, self._indice_originales):
            for clave, i in indice.items():
                if clave.startswith(consulta):
                    empiezan.setdefault(i, None)
                elif patron.search(clave):
                    contienen.setdefault(i, None)
        contienen = [i for i in contienen if i not in empiezan]
        # Entre los que encajan, primero los títulos cortos y luego los más votados.
        votos = self.datos["votos"].fillna(0)
        ordenar = lambda ids: sorted(ids, key=lambda i: (len(self.datos.at[i, "titulo"]), -votos[i]))
        return [self.datos.at[i, "titulo"] for i in (ordenar(empiezan) + ordenar(contienen))[:limite]]

    def indice_de(self, titulo):
        clave = normalizar(titulo)
        i = self._indice_titulos.get(clave)
        return self._indice_originales.get(clave) if i is None else i

    # --- Recomendación ----------------------------------------------------- #

    def similitudes(self, i):
        """Afinidad entre el título i y todos los demás (de 0 a 1).

        Es la media geométrica de dos medidas que se complementan:

        - El coseno entre los vectores completos: premia compartir cosas raras (un director,
          un actor), pero sale bajo aunque dos títulos se parezcan mucho, porque cada uno
          tiene muchas etiquetas propias.
        - La afinidad por aspectos: el coseno dentro de cada grupo (¿cuánto se parecen sus
          géneros? ¿y su reparto?), en media ponderada por los pesos. Dice en cuántos
          aspectos se parecen, pero por sí sola da un 100 % en géneros a dos dramas cualquiera.

        Con la media geométrica, un título solo puntúa alto si destaca en las dos.
        El producto escalar solo suma las características que tienen en común, así que
        basta con recorrer las del título i y sumar en los títulos que también las tienen.
        """
        n = len(self.datos)
        producto = np.zeros(n)
        aspectos = np.zeros(n)
        for grupo, peso in self.pesos.items():
            if not self.normas_grupo[grupo][i]:
                continue
            comun = np.zeros(n)
            for etiqueta in self.etiquetas[i][grupo]:
                clave = (grupo, etiqueta)
                if clave in self.indice:
                    comun[self.indice[clave]] += self.idf[clave] ** 2
            producto += peso ** 2 * comun
            aspectos += peso * _dividir(comun, self.normas_grupo[grupo] * self.normas_grupo[grupo][i])
        coseno = _dividir(producto, self.normas * self.normas[i])
        aspectos = _dividir(aspectos, np.sqrt(self.pesos_presentes * self.pesos_presentes[i]))
        return np.sqrt(coseno * aspectos)

    def _factor_calidad(self):
        """Multiplicador por título (se calcula una sola vez) que premia nota y popularidad.

        - Nota: ante dos títulos igual de parecidos, gana el mejor valorado (hasta un 3 %).
          Una nota con muy pocos votos no es fiable, así que en ese caso se usa la mediana.
        - Popularidad: es más probable que te guste lo que ha visto más gente (hasta un 15 %).
        """
        if getattr(self, "_factor", None) is None:
            nota = self.datos["nota"].copy()
            if self.datos["votos"].notna().any():
                nota[self.datos["votos"].fillna(0) < 20] = np.nan
            nota = nota.fillna(self.datos["nota"].median()).fillna(0).to_numpy()
            factor = 1 + 0.03 * nota / 10
            votos = np.log1p(self.datos["votos"].fillna(0).to_numpy())
            if votos.max() > 0:
                factor = factor * (1 + 0.15 * votos / votos.max())
            self._factor = factor
        return self._factor

    def puntuaciones(self, i):
        """Puntuación final de todos los títulos respecto al título i (el propio queda a -1)."""
        puntuacion = self.similitudes(i) * self._factor_calidad()
        puntuacion[i] = -1  # nunca recomendar el propio título
        return puntuacion

    def recomendar(self, titulo, cantidad=10, tipo=None):
        """Devuelve los `cantidad` títulos más parecidos a `titulo`.

        tipo: None para todo, o el texto del tipo ('Movie', 'TV Show') para filtrar.
        """
        i = self.indice_de(titulo)
        if i is None:
            raise KeyError(f"No encuentro '{titulo}' en el catálogo.")

        puntuacion = self.puntuaciones(i)
        if tipo:
            puntuacion[(self.datos["tipo"] != tipo).to_numpy()] = -1

        mejores = np.argsort(-puntuacion)[:cantidad]
        return [self._crear_recomendacion(i, j, puntuacion[j]) for j in mejores if puntuacion[j] > 0]

    def _crear_recomendacion(self, origen, j, puntuacion):
        fila = self.datos.iloc[j]
        coincidencias = {}
        for grupo in ("director", "reparto", "generos", "temas", "pais"):
            comunes = self.etiquetas[origen][grupo] & self.etiquetas[j][grupo]
            if comunes:
                coincidencias[grupo] = sorted(self.originales.get((grupo, e), e) for e in comunes)
        return Recomendacion(
            titulo=fila["titulo"],
            tipo=fila["tipo"],
            similitud=round(min(puntuacion, 1.0) * 100, 1),
            nota=fila["nota"],
            anio="" if pd.isna(fila["anio"]) else str(fila["anio"]),
            generos="" if pd.isna(fila["generos"]) else str(fila["generos"]),
            descripcion="" if pd.isna(fila["descripcion"]) else str(fila["descripcion"]),
            coincidencias=coincidencias,
        )

    def tipos(self):
        return sorted(self.datos["tipo"].dropna().unique())


def _dividir(a, b):
    """a / b elemento a elemento, con 0 donde b es 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, 0.0)


def buscar_csv(carpeta):
    """CSV que usará la aplicación: el catálogo de TMDb más reciente o, si no hay,
    cualquier otro CSV de la carpeta data/ (p. ej. el dataset de Kaggle)."""
    carpeta = Path(carpeta)
    por_fecha = lambda rutas: sorted(rutas, key=lambda r: r.stat().st_mtime, reverse=True)
    csvs = por_fecha(carpeta.glob("catalogo_netflix_*.csv")) or por_fecha(carpeta.glob("*.csv"))
    return csvs[0] if csvs else None


if __name__ == "__main__":
    # Prueba rápida por terminal: python recomendador.py "Narcos"
    import sys

    ruta = buscar_csv(Path(__file__).parent / "data")
    if not ruta:
        sys.exit("Pon el CSV del dataset de Netflix en la carpeta data/.")
    motor = Recomendador.desde_csv(ruta)
    titulo = " ".join(sys.argv[1:]) or motor.datos.at[0, "titulo"]
    for r in motor.recomendar(titulo):
        print(f"{r.similitud:5.1f}%  {r.titulo}  ({r.tipo}, {r.anio}, nota {r.nota})")
