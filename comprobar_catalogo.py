"""Comprueba que el catálogo recién descargado está completo antes de publicarlo.

TMDb a veces devuelve el catálogo a medias (una caída, o los datos de JustWatch a mitad de
actualizarse). Publicarlo dejaría la web sin cientos de títulos, así que se para si:

- tiene menos de MINIMO títulos, o
- tiene más de un MARGEN menos que el último catálogo publicado (ULTIMA_ACTUALIZACION.md).

Uso:
    python comprobar_catalogo.py            # Netflix España: sale con error si parece incompleto
    python comprobar_catalogo.py --pais US  # lo mismo con Netflix USA
    python comprobar_catalogo.py --forzar   # publica aunque haya bajado (si de verdad ha bajado)
"""

import argparse
import csv
import re
import sys
from pathlib import Path

CARPETA = Path(__file__).parent
MINIMO = 5000
MARGEN = 0.05  # un catálogo de Netflix no pierde más de un 5 % de un mes a otro
PAISES = {"ES": "España", "US": "USA"}  # cómo aparece cada país en ULTIMA_ACTUALIZACION.md


def titulos_anteriores(ruta=CARPETA / "ULTIMA_ACTUALIZACION.md", pais="ES"):
    """Número de títulos del último catálogo publicado del país, o None si no se sabe.

    El archivo tiene una línea por país («- Netflix USA: 7123 títulos.»). Antes solo había
    España, en el formato «Última actualización del catálogo: 2026-11-27 (9110 títulos).»
    """
    if not Path(ruta).exists():
        return None
    contenido = Path(ruta).read_text(encoding="utf-8")
    encontrado = re.search(rf"Netflix {PAISES[pais]}: (\d+) títulos", contenido)
    if not encontrado and pais == "ES":
        encontrado = re.search(r"\((\d+) títulos\)", contenido)
    return int(encontrado.group(1)) if encontrado else None


def problema(total, anterior, minimo=MINIMO, margen=MARGEN):
    """Texto con el motivo para no publicar, o None si el catálogo parece completo."""
    if total < minimo:
        return f"Solo hay {total} títulos (mínimo {minimo})."
    if anterior and total < anterior * (1 - margen):
        perdidos = anterior - total
        return (f"Hay {total} títulos, {perdidos} menos que el último publicado ({anterior}): "
                f"más de un {margen:.0%} menos de golpe.")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pais", default="ES", choices=sorted(PAISES), type=str.upper)
    parser.add_argument("--csv", type=Path, help="por defecto, data/catalogo_netflix_<país>.csv")
    parser.add_argument("--forzar", action="store_true", help="publicar aunque el catálogo haya bajado")
    args = parser.parse_args()

    ruta = args.csv or CARPETA / "data" / f"catalogo_netflix_{args.pais.lower()}.csv"
    with open(ruta, encoding="utf-8") as archivo:
        total = sum(1 for _ in csv.DictReader(archivo))
    anterior = titulos_anteriores(pais=args.pais)
    print(f"Netflix {PAISES[args.pais]}: {total} títulos descargados "
          f"(último publicado: {anterior or 'desconocido'}).")

    motivo = problema(total, None if args.forzar else anterior)
    if motivo:
        sys.exit(f"El catálogo parece incompleto: no se publica. {motivo}\n"
                 "La web se queda como estaba. Si el catálogo ha bajado de verdad, lánzalo a mano "
                 "desde Actions marcando «forzar».")
    print("El catálogo parece completo.")


if __name__ == "__main__":
    main()
