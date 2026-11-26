"""Precalcula todas las recomendaciones y las guarda como JSON para la web.

La web es estática (Cloudflare Pages, sin servidor): no puede ejecutar Python. Por eso el
motor calcula aquí, de una vez, las recomendaciones de cada título del catálogo y la web
solo tiene que leerlas.

Genera en web/datos/:
- catalogo.json      lista ligera de todos los títulos (buscador, carteles, minutos).
- fichas/NNN.json    detalle y recomendaciones, en bloques de 100 títulos para que la
                     web descargue solo el bloque que necesita.

Uso:
    python exportar_web.py
"""

import json
import re
import shutil
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from recomendador import Recomendador, buscar_csv

CARPETA = Path(__file__).parent
SALIDA = CARPETA / "web" / "datos"
POR_BLOQUE = 100
RECOMENDACIONES = 12  # por cada lista: todo, películas y series
TIPOS = {"Movie": "p", "TV Show": "s"}
NOMBRES_MOTIVO = {
    "director": ("Dirección", "Creación"), "reparto": ("Reparto",), "temas": ("Temas",),
    "generos": ("Géneros",), "pais": ("País",),
}


def texto(valor):
    return "" if pd.isna(valor) else str(valor).strip()


def minutos(duracion):
    """'120 min' -> 120; las series no tienen una duración comparable."""
    m = re.match(r"(\d+)\s*min", texto(duracion))
    return int(m.group(1)) if m else 0


def motivos(motor, origen, j):
    """Las tres razones más fuertes por las que j se parece a origen, en orden de peso."""
    rec = motor._crear_recomendacion(origen, j, 0)
    es_serie = motor.datos.at[j, "tipo"] == "TV Show"
    salida = []
    for grupo in ("director", "reparto", "temas", "generos", "pais"):
        if grupo in rec.coincidencias:
            nombres = NOMBRES_MOTIVO[grupo]
            etiqueta = nombres[1] if grupo == "director" and es_serie and len(nombres) > 1 else nombres[0]
            salida.append([etiqueta, rec.coincidencias[grupo][:3]])
        if len(salida) == 3:
            break
    return salida


def main():
    ruta = buscar_csv(CARPETA / "data")
    print(f"Cargando {ruta.name}…")
    motor = Recomendador.desde_csv(ruta)
    datos = motor.datos
    posters, fondos = [texto(v) for v in datos["cartel"]], [texto(v) for v in datos["fondo"]]
    tmdb = [texto(v).split(".")[0] for v in datos["tmdb_id"]]
    duraciones = [texto(v) for v in datos["duracion"]]

    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    (SALIDA / "fichas").mkdir(parents=True)

    # --- catalogo.json -------------------------------------------------------- #
    titulos = []
    for i, fila in datos.iterrows():
        alias = {texto(fila["titulo_original"]), texto(fila["titulo_ingles"])} - {"", fila["titulo"]}
        titulos.append([
            fila["titulo"],
            " | ".join(sorted(alias)),
            texto(fila["anio"]),
            TIPOS.get(fila["tipo"], "p"),
            posters[i],
            int(fila["votos"]) if pd.notna(fila["votos"]) else 0,
            minutos(duraciones[i]) if fila["tipo"] == "Movie" else 0,
        ])
    catalogo = {
        "actualizado": date.fromtimestamp(ruta.stat().st_mtime).isoformat(),
        "pais": "ES",
        "columnas": ["titulo", "alias", "anio", "tipo", "poster", "votos", "minutos"],
        "titulos": titulos,
    }
    (SALIDA / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")))

    # --- fichas/NNN.json ------------------------------------------------------ #
    es_peli = (datos["tipo"] == "Movie").to_numpy()
    es_serie = (datos["tipo"] == "TV Show").to_numpy()
    inicio = time.time()
    bloque = {}
    for i in range(len(datos)):
        puntuacion = motor.puntuaciones(i)
        listas = {}
        for clave, mascara in (("t", None), ("p", es_peli), ("s", es_serie)):
            p = puntuacion if mascara is None else np.where(mascara, puntuacion, -1)
            mejores = np.argpartition(-p, RECOMENDACIONES)[:RECOMENDACIONES]
            mejores = mejores[np.argsort(-p[mejores])]
            listas[clave] = [int(j) for j in mejores if p[j] > 0]

        recomendados = {}
        for j in dict.fromkeys(listas["t"] + listas["p"] + listas["s"]):
            recomendados[j] = [round(min(float(puntuacion[j]), 1.0) * 100), motivos(motor, i, j)]

        fila = datos.iloc[i]
        reparto = [r for r in texto(fila["reparto"]).split(", ") if r][:5]
        bloque[i] = {
            "d": texto(fila["descripcion"]),
            "g": texto(fila["generos"]),
            "dir": texto(fila["director"]),
            "rep": reparto,
            "dur": duraciones[i],
            "nota": round(float(fila["nota"]), 1) if pd.notna(fila["nota"]) else None,
            "bd": fondos[i],
            "tmdb": tmdb[i],
            "r": {str(j): v for j, v in recomendados.items()},
            "l": listas,
        }
        if (i + 1) % POR_BLOQUE == 0 or i == len(datos) - 1:
            numero = i // POR_BLOQUE
            (SALIDA / "fichas" / f"{numero:03d}.json").write_text(
                json.dumps(bloque, ensure_ascii=False, separators=(",", ":"))
            )
            bloque = {}
            print(f"\r  {i + 1}/{len(datos)} títulos ({time.time() - inicio:.0f} s)", end="", flush=True)

    total = sum(f.stat().st_size for f in SALIDA.rglob("*.json")) / 1e6
    print(f"\nListo: {len(datos)} títulos exportados a {SALIDA.relative_to(CARPETA)} ({total:.1f} MB).")


if __name__ == "__main__":
    main()
