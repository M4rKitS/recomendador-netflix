# Recomendador de Netflix

Aplicación de escritorio en Python que recomienda películas y series del catálogo **actual** de
Netflix España, descargado de la API de TMDb.
Escribes un título que te haya gustado y te propone otros parecidos, explicando por qué
(mismo director, actores en común, géneros, país…).

Tiene dos interfaces: una aplicación de escritorio con `tkinter` y una **web pública,
«¿Qué veo ahora?»**, pensada para Cloudflare Pages.

Proyecto de portfolio del módulo de Python del Máster Full Stack de Conquer Blocks.

## Tecnologías

| Módulo | Para qué se usa |
|---|---|
| `tkinter` | Interfaz gráfica: buscador con sugerencias, botones, tabla de resultados y ficha de detalle |
| `pandas` | Leer el CSV y limpiar los datos |
| `numpy` | Calcular las puntuaciones de similitud de todo el catálogo a la vez |
| `re` | Limpiar texto y separar listas (`"Dramas, Comedies"` → `["dramas", "comedies"]`) |
| `nltk` | Quitar palabras vacías y reducir palabras a su raíz en las sinopsis (`luchan` → `luch`) |
| `urllib`, `json`, `concurrent.futures` | Descargar el catálogo de la API de TMDb con varias peticiones en paralelo |

## Instalación

Hace falta **Python 3.10 o superior con Tk 8.6+**. En macOS, el Python que trae el sistema
(3.9 con Tk 8.5) está obsoleto y la ventana se queda colgada; instala uno nuevo:

```bash
brew install python@3.13 python-tk@3.13
```

Crea el entorno virtual e instala las dependencias:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m nltk.downloader stopwords
```

## Datos: el catálogo actual de Netflix

Los datasets de Netflix de Kaggle se quedaron en 2021, así que el proyecto genera su propio
catálogo con la API gratuita de [TMDb](https://www.themoviedb.org/). TMDb sabe qué títulos
están disponibles en Netflix en cada país (gracias a JustWatch), y de cada uno descargamos
sinopsis, géneros, palabras clave temáticas, país, reparto, dirección (o creadores, en las
series), clasificación por edades y nota. Si TMDb no tiene la sinopsis en castellano, se usa la
inglesa, y los títulos en otros alfabetos (오징어 게임) se sustituyen por su título en inglés.

1. Crea una cuenta gratuita en [themoviedb.org](https://www.themoviedb.org/signup).
2. Ve a **Ajustes → API** ([enlace directo](https://www.themoviedb.org/settings/api)) y solicita
   una clave de tipo *Developer* para uso personal.
3. Copia `.env.example` como `.env` y pega tu clave en `TMDB_API_KEY`. El archivo `.env` no se
   sube a GitHub.
4. Descarga el catálogo (tarda unos minutos):

   ```bash
   python descargar_catalogo.py
   ```

   Se guarda en `data/catalogo_netflix_es.csv`. Para otro país: `--pais MX`, `--pais AR`…
   Vuelve a ejecutarlo cuando quieras para tener el catálogo al día.

La aplicación usa el catálogo de TMDb más reciente de `data/`. Si no hay ninguno, también acepta
los CSV antiguos de Kaggle (por ejemplo, [Netflix Movies and TV Shows 2021](https://www.kaggle.com/datasets/satpreetmakhija/netflix-movies-and-tv-shows-2021)),
porque reconoce sus nombres de columna.

> Este producto usa la API de TMDb pero no está avalado ni certificado por TMDb.
> Datos de disponibilidad por país: JustWatch.

## Uso

```bash
python app.py
```

1. Empieza a escribir un título: aparecen sugerencias (no importan mayúsculas ni acentos, y
   también puedes escribir el título original o el inglés: "Money Heist" encuentra
   "La casa de papel").
2. Pulsa **Recomendar** o Intro.
3. Filtra por **Películas** o **Series** y elige cuántas recomendaciones ver.
4. Haz clic en un resultado para leer su sinopsis y por qué te lo recomendamos.

Prueba rápida desde la terminal:

```bash
python recomendador.py "La casa de papel"
```

## La web: «¿Qué veo ahora?»

Una página estática (HTML, CSS y JavaScript, sin frameworks ni servidor) en la carpeta `web/`,
pensada como una sala de proyección: la portada es una pared de carteles reales del catálogo
con el buscador encima, y la luz ambiente de la página toma el color del cartel del título que
eliges. Debajo, la recomendación más parecida en grande y diez más con su afinidad y sus
motivos; «Cómo decide», que ilumina los pesos del motor en los que coinciden de verdad; y «Esta
noche», que cuenta cuántas películas caben en el tiempo que tienes. Incluye filtro de películas
o series, ficha de detalle y enlace para compartir (`?t=Breaking Bad`).

Como Cloudflare Pages no ejecuta Python, el motor calcula **de antemano** las recomendaciones
de todos los títulos y la web solo las lee:

```bash
python exportar_web.py   # unos 15 s; genera web/datos/ (catálogo + 99 bloques de fichas)
```

Para verla en local:

```bash
python -m http.server 8000 --directory web
```

y abre http://localhost:8000. Para publicarla en Cloudflare Pages:

```bash
npx wrangler pages deploy web --project-name queveoahora
```

Para actualizarla a mano: `descargar_catalogo.py` → `exportar_web.py` → volver a publicar.

### Actualización automática cada mes

`.github/workflows/actualizar-web.yml` lo hace solo el **día 1 de cada mes** (y cuando quieras,
con *Run workflow* en la pestaña *Actions* de GitHub). También se lanza sola cada vez que se
sube un cambio de la web (`web/`) o del motor (`*.py`), así que un arreglo se publica sin tocar nada:

1. Instala las dependencias y pasa las pruebas del motor.
2. Descarga el catálogo actual de Netflix España desde TMDb.
3. Comprueba que el catálogo está completo (si TMDb falla a medias, no publica nada).
4. Precalcula todas las recomendaciones con `exportar_web.py`.
5. Publica en Cloudflare Pages.
6. Anota la fecha en `ULTIMA_ACTUALIZACION.md` con un pequeño commit, que además evita que
   GitHub desactive la tarea programada por falta de actividad.

Necesita el proyecto en su propio repositorio de GitHub y tres secretos en
*Settings → Secrets and variables → Actions*:

| Secreto | De dónde sale |
| --- | --- |
| `TMDB_API_KEY` | La misma clave de TMDb del archivo `.env`. |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → *My Profile → API Tokens*, plantilla con permiso *Cloudflare Pages: Edit*. |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare → *Workers & Pages*, columna de la derecha. |

## Cómo funciona el motor

Es un **recomendador basado en contenido**: no usa valoraciones de otros usuarios, sino las
características de cada título.

1. **Limpieza.** Cada título se convierte en grupos de etiquetas: géneros, temas (las palabras
   clave de TMDb, como "heist" o "1980s"), dirección, los seis primeros actores, país, clasificación por edades, tipo (película o serie) y palabras clave de
   la sinopsis (sin palabras vacías y reducidas a su raíz con NLTK). El idioma de las sinopsis
   (castellano o inglés) se detecta solo en cada una.
2. **Rareza de cada etiqueta (IDF).** Compartir algo raro informa más que compartir algo común:
   que dos títulos tengan el mismo director pesa mucho más que ser ambos "Drama". Las etiquetas
   que solo tiene un título (una palabra rara de su sinopsis, un actor que no sale en nada más)
   se descartan: nunca pueden coincidir y solo rebajarían todas sus afinidades.
3. **Un vector por título.** Cada etiqueta vale *peso de su grupo × rareza*. Los pesos son:

   | Grupo | Peso |
   |---|---|
   | Géneros | 3 |
   | Temas (palabras clave de TMDb) | 2 |
   | Dirección | 2 |
   | Reparto | 2 |
   | Palabras clave de la sinopsis | 1,5 |
   | País | 1 |
   | Clasificación por edades | 0,75 |
   | Tipo | 0,5 |

4. **Afinidad: dos medidas en una.** El motor calcula:
   - el **coseno** entre los vectores completos, que premia compartir lo raro pero sale bajo
     incluso entre títulos muy parecidos, porque cada uno tiene muchas etiquetas propias;
   - la **afinidad por aspectos**: el coseno dentro de cada grupo (¿cuánto se parecen sus
     géneros?, ¿y su reparto?), en media ponderada por los pesos.

   La afinidad final es la **media geométrica** de las dos (0 % = nada en común, 100 % =
   idénticos): solo puntúa alto lo que destaca en ambas. Con solo el coseno, la mejor
   recomendación de un título rondaba el 15 % y la décima el 9 %; ahora rondan el 36 % y el
   23 %, y las listas apenas cambian (las secuelas y spin-offs siguen arriba).
   Un índice invertido (etiqueta → títulos que la tienen) permite comparar un título contra
   miles en un milisegundo. Si a un título le falta un dato (muchas series no tienen
   director), ese grupo simplemente no cuenta.
5. **Ajustes finales.** Entre títulos igual de parecidos se prefieren los más populares (hasta
   un 15 % extra para el más votado) y los mejor valorados (hasta un 3 %; las notas con menos
   de 20 votos no cuentan). Sin este ajuste, series casi desconocidas con muy pocos datos
   aparecían arriba solo por coincidir en un par de géneros.

   Por qué no basta la afinidad por aspectos sola: una película con un único género muy común
   ("Dramas") coincide al 100 % en géneros con cientos de dramas, y eso pesaría más que
   compartir director y actores. Al combinarla con el coseno del vector completo, las
   coincidencias raras (Martin Scorsese, Robert De Niro) siguen pesando lo que deben.

Cómo leer el porcentaje: 40 % o más es de la misma familia (secuelas, spin-offs); entre 25 y
40 %, muy parecida; por debajo, parecida en el tipo de historia.

Los pesos están en el diccionario `PESOS` de `recomendador.py` y se pueden ajustar.

## Pruebas

```bash
python -m unittest discover -s tests -t .
```

Las pruebas no necesitan red ni clave: usan CSV pequeños con títulos inventados (uno con el
formato de Kaggle y otro con el del catálogo de TMDb) y un cliente de TMDb falso para el script
de descarga.

## Estructura

```
.
├── app.py                  # Interfaz gráfica con tkinter
├── recomendador.py         # Carga de datos y motor de recomendación
├── descargar_catalogo.py   # Descarga el catálogo actual de Netflix desde TMDb
├── exportar_web.py         # Precalcula las recomendaciones en JSON para la web
├── web/                    # La web pública (index.html, estilo.css, app.js, datos/)
├── data/                   # Catálogo descargado (no se sube al repositorio)
├── tests/                  # Pruebas unitarias y CSV de ejemplo
├── .github/workflows/      # Actualización automática mensual de la web
├── .env.example            # Plantilla para la clave de TMDb
└── requirements.txt
```
