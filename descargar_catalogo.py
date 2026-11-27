"""Descarga el catálogo actual de Netflix de un país usando la API de TMDb.

TMDb (The Movie Database) sabe qué títulos están disponibles en cada plataforma y país
(datos de JustWatch). Este script:

1. Pide a TMDb todas las películas y series disponibles hoy en Netflix en el país elegido.
2. Descarga la ficha de cada una: sinopsis, géneros, país, reparto, director, nota...
   y las recomendaciones del público de TMDb («a quien le gustó esto también le gustó...»).
3. Lo guarda todo en data/catalogo_netflix_<pais>.csv, listo para el recomendador.

Uso:
    python descargar_catalogo.py            # Netflix España
    python descargar_catalogo.py --pais MX  # Netflix México
    python descargar_catalogo.py --pais US --idioma en-US  # Netflix USA, en inglés (web /en/)

Necesita una clave de la API de TMDb en el archivo .env (ver .env.example).
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

API = "https://api.themoviedb.org/3"
NETFLIX = 8  # identificador de Netflix como plataforma en TMDb
CARPETA = Path(__file__).parent
MAX_ACTORES = 8
HILOS = 8  # peticiones en paralelo (TMDb permite unas 40 por segundo)

COLUMNAS = [
    "tmdb_id", "title", "original_title", "english_title", "content_type", "description",
    "director", "genres", "keywords", "cast", "country", "rating", "tmdb_score", "votes",
    "release_year", "duration", "popularity", "poster", "backdrop", "recommendations",
]


# --------------------------------------------------------------------------- #
# Clave de la API
# --------------------------------------------------------------------------- #

def leer_clave():
    """Lee TMDB_API_KEY del entorno o del archivo .env (sin dependencias extra)."""
    clave = os.environ.get("TMDB_API_KEY")
    archivo = CARPETA / ".env"
    if not clave and archivo.exists():
        for linea in archivo.read_text().splitlines():
            nombre, _, valor = linea.partition("=")
            if nombre.strip() == "TMDB_API_KEY":
                clave = valor.strip().strip('"').strip("'")
    if not clave:
        sys.exit(
            "Falta la clave de TMDb.\n"
            "Copia .env.example como .env y pega tu clave en TMDB_API_KEY (ver README)."
        )
    return clave


class ClienteTMDb:
    """Cliente mínimo de la API de TMDb con reintentos."""

    def __init__(self, clave, idioma):
        self.idioma = idioma
        # TMDb da dos tipos de credencial: el "token de lectura" (largo, empieza por eyJ)
        # va en la cabecera; la "clave de API" corta va como parámetro de la URL.
        self.token = clave if clave.startswith("eyJ") else None
        self.clave = None if self.token else clave

    def get(self, ruta, **parametros):
        parametros.setdefault("language", self.idioma)
        if self.clave:
            parametros["api_key"] = self.clave
        url = f"{API}{ruta}?{urllib.parse.urlencode(parametros)}"
        cabeceras = {"Accept": "application/json"}
        if self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"

        for intento in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras), timeout=20) as r:
                    return json.load(r)
            except urllib.error.HTTPError as error:
                if error.code == 401:
                    sys.exit("TMDb rechaza la clave (error 401). Revisa TMDB_API_KEY en .env.")
                if error.code == 404:
                    return None
                if error.code != 429 and error.code < 500:
                    raise
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(2 ** intento)  # demasiadas peticiones o fallo de red: esperar y reintentar
        raise RuntimeError(f"TMDb no responde: {ruta}")


# --------------------------------------------------------------------------- #
# Descarga
# --------------------------------------------------------------------------- #

def ids_en_netflix(cliente, tipo, pais):
    """Todos los ids de películas ('movie') o series ('tv') disponibles en Netflix en el país.

    /discover devuelve como mucho 500 páginas, así que si hiciera falta se trocea por año.
    """
    def recorrer(**filtros):
        ids, pagina, total = [], 1, 1
        while pagina <= min(total, 500):
            datos = cliente.get(
                f"/discover/{tipo}", watch_region=pais, with_watch_providers=NETFLIX,
                with_watch_monetization_types="flatrate", sort_by="popularity.desc",
                page=pagina, **filtros,
            )
            ids += [r["id"] for r in datos["results"]]
            total = datos["total_pages"]
            pagina += 1
        return ids, total

    ids, total = recorrer()
    if total > 500:
        campo = "primary_release_date" if tipo == "movie" else "first_air_date"
        ids = []
        for anio in range(1900, date.today().year + 2):
            ids += recorrer(**{f"{campo}.gte": f"{anio}-01-01", f"{campo}.lte": f"{anio}-12-31"})[0]
    return list(dict.fromkeys(ids))  # sin duplicados, en el mismo orden


def nombres(lista, clave="name"):
    return ", ".join(e[clave] for e in lista if e.get(clave))


def es_alfabeto_latino(texto):
    """False para títulos en coreano, japonés, tailandés... que no se pueden buscar con un teclado español."""
    letras = [c for c in texto if c.isalpha()]
    return not letras or sum(c.isascii() or "\u00c0" <= c <= "\u024f" for c in letras) / len(letras) > 0.8


def traduccion_inglesa(ficha):
    """Título y sinopsis en inglés (preferimos la versión de EE. UU.)."""
    traducciones = [t for t in ficha.get("translations", {}).get("translations", []) if t["iso_639_1"] == "en"]
    traducciones.sort(key=lambda t: t["iso_3166_1"] != "US")
    datos = traducciones[0]["data"] if traducciones else {}
    return (datos.get("title") or datos.get("name") or ""), datos.get("overview") or ""


def completar_textos(fila, ficha):
    """Rellena con la versión inglesa lo que TMDb no tiene traducido al castellano.

    - Sinopsis vacía -> sinopsis en inglés (mejor algo que nada para comparar).
    - Título en otro alfabeto (오징어 게임) -> título en inglés (Squid Game).
    """
    titulo_en, sinopsis_en = traduccion_inglesa(ficha)
    fila["english_title"] = titulo_en
    if not fila["description"]:
        fila["description"] = sinopsis_en
    if titulo_en and not es_alfabeto_latino(fila["title"]):
        fila["title"] = titulo_en
    return fila


def recomendaciones_publico(ficha):
    """Ids de TMDb que su comunidad recomienda a quien le gustó este título, en orden.

    Son del mismo tipo (películas para una película, series para una serie) y pueden no
    estar en Netflix: el recomendador se queda solo con las que están en el catálogo.
    """
    resultados = (ficha.get("recommendations") or {}).get("results", [])
    return " ".join(str(r["id"]) for r in resultados if r.get("id"))


def imagenes(ficha):
    """Rutas del cartel y la imagen de fondo en el CDN de TMDb, y su popularidad actual."""
    return {
        "popularity": round(ficha.get("popularity") or 0, 2),
        "recommendations": recomendaciones_publico(ficha),
        "poster": ficha.get("poster_path") or "",
        "backdrop": ficha.get("backdrop_path") or "",
    }


def texto_temporadas(numero, idioma):
    """3 -> '3 temporadas' (o '3 seasons' si el catálogo se descarga en inglés)."""
    if not numero:
        return ""
    if idioma.startswith("en"):
        return f"{numero} season{'s' if numero != 1 else ''}"
    return f"{numero} temporada{'s' if numero != 1 else ''}"


def clasificacion_pelicula(ficha, pais):
    for region in ficha.get("release_dates", {}).get("results", []):
        if region["iso_3166_1"] == pais:
            for estreno in region["release_dates"]:
                if estreno.get("certification"):
                    return estreno["certification"]
    return ""


def clasificacion_serie(ficha, pais):
    for region in ficha.get("content_ratings", {}).get("results", []):
        if region["iso_3166_1"] == pais and region.get("rating"):
            return region["rating"]
    return ""


def ficha_pelicula(cliente, tmdb_id, pais):
    f = cliente.get(f"/movie/{tmdb_id}", append_to_response="credits,release_dates,keywords,translations,recommendations")
    if not f:
        return None
    equipo = f.get("credits", {})
    directores = [p for p in equipo.get("crew", []) if p.get("job") == "Director"]
    return completar_textos({
        "tmdb_id": f["id"],
        "title": f.get("title", ""),
        "original_title": f.get("original_title", ""),
        "content_type": "Movie",
        "description": f.get("overview", ""),
        "director": nombres(directores),
        "genres": nombres(f.get("genres", [])),
        # Palabras clave de TMDb (en inglés): "heist", "1980s", "small town"...
        "keywords": nombres(f.get("keywords", {}).get("keywords", [])),
        "cast": nombres(equipo.get("cast", [])[:MAX_ACTORES]),
        "country": nombres(f.get("production_countries", [])),
        "rating": clasificacion_pelicula(f, pais),
        "tmdb_score": f.get("vote_average") or "",
        "votes": f.get("vote_count", 0),
        "release_year": (f.get("release_date") or "")[:4],
        "duration": f"{f['runtime']} min" if f.get("runtime") else "",
        **imagenes(f),
    }, f)


def ficha_serie(cliente, tmdb_id, pais):
    f = cliente.get(f"/tv/{tmdb_id}", append_to_response="aggregate_credits,content_ratings,keywords,translations,recommendations")
    if not f:
        return None
    temporadas = f.get("number_of_seasons") or 0
    return completar_textos({
        "tmdb_id": f["id"],
        "title": f.get("name", ""),
        "original_title": f.get("original_name", ""),
        "content_type": "TV Show",
        "description": f.get("overview", ""),
        # Las series no tienen "director": usamos a sus creadores, que cumplen ese papel.
        "director": nombres(f.get("created_by", [])),
        "genres": nombres(f.get("genres", [])),
        "keywords": nombres(f.get("keywords", {}).get("results", [])),
        "cast": nombres(f.get("aggregate_credits", {}).get("cast", [])[:MAX_ACTORES]),
        "country": nombres(f.get("production_countries", [])) or ", ".join(f.get("origin_country", [])),
        "rating": clasificacion_serie(f, pais),
        "tmdb_score": f.get("vote_average") or "",
        "votes": f.get("vote_count", 0),
        "release_year": (f.get("first_air_date") or "")[:4],
        "duration": texto_temporadas(temporadas, getattr(cliente, "idioma", "es-ES")),
        **imagenes(f),
    }, f)


def descargar_fichas(cliente, tipo, ids, pais):
    funcion = ficha_pelicula if tipo == "movie" else ficha_serie
    fichas = []
    with ThreadPoolExecutor(HILOS) as hilos:
        tareas = [hilos.submit(funcion, cliente, i, pais) for i in ids]
        for n, tarea in enumerate(as_completed(tareas), 1):
            ficha = tarea.result()
            if ficha and ficha["title"]:
                fichas.append(ficha)
            if n % 100 == 0 or n == len(ids):
                print(f"\r  fichas: {n}/{len(ids)}", end="", flush=True)
    print()
    return fichas


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pais", default="ES", help="código del país (ES, MX, AR, US...)")
    parser.add_argument("--idioma", default="es-ES", help="idioma de títulos y sinopsis")
    args = parser.parse_args()
    pais = args.pais.upper()

    cliente = ClienteTMDb(leer_clave(), args.idioma)
    filas = []
    for tipo, nombre in (("movie", "películas"), ("tv", "series")):
        print(f"Buscando {nombre} en Netflix {pais}…")
        ids = ids_en_netflix(cliente, tipo, pais)
        print(f"  {len(ids)} {nombre}")
        filas += descargar_fichas(cliente, tipo, ids, pais)

    salida = CARPETA / "data" / f"catalogo_netflix_{pais.lower()}.csv"
    salida.parent.mkdir(exist_ok=True)
    with open(salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"\nListo: {len(filas)} títulos guardados en {salida.relative_to(CARPETA)} ({date.today()}).")


if __name__ == "__main__":
    main()
