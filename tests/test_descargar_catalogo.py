"""Pruebas del script de descarga con un cliente falso (sin red ni clave de TMDb)."""
import unittest

from descargar_catalogo import es_alfabeto_latino, ficha_pelicula, ficha_serie, ids_en_netflix

PELICULA = {
    "id": 10, "title": "La deriva", "original_title": "Space Drift", "overview": "Astronautas en órbita.",
    "genres": [{"name": "Drama"}, {"name": "Ciencia ficción"}],
    "production_countries": [{"name": "United States of America"}],
    "vote_average": 7.1, "vote_count": 3000, "poster_path": "/cartel.jpg", "popularity": 12.345, "release_date": "2020-05-01", "runtime": 120,
    "credits": {
        "cast": [{"name": f"Actor {n}"} for n in range(12)],
        "crew": [{"name": "Eva Stone", "job": "Director"}, {"name": "Otro", "job": "Writer"}],
    },
    "keywords": {"keywords": [{"name": "space"}, {"name": "astronaut"}]},
    "translations": {"translations": [
        {"iso_639_1": "en", "iso_3166_1": "GB", "data": {"title": "Space Drift (UK)", "overview": ""}},
        {"iso_639_1": "en", "iso_3166_1": "US", "data": {"title": "Space Drift", "overview": "Astronauts."}},
    ]},
    "release_dates": {"results": [
        {"iso_3166_1": "US", "release_dates": [{"certification": "PG-13"}]},
        {"iso_3166_1": "ES", "release_dates": [{"certification": ""}, {"certification": "12"}]},
    ]},
}

SERIE = {
    "id": 20, "name": "오징어 게임", "original_name": "오징어 게임", "overview": "",
    "keywords": {"results": [{"name": "survival"}, {"name": "game"}]},
    "translations": {"translations": [
        {"iso_639_1": "en", "iso_3166_1": "US", "data": {"name": "Squid Game", "overview": "A deadly game."}},
    ]},
    "genres": [{"name": "Crimen"}], "production_countries": [], "origin_country": ["ES"],
    "created_by": [{"name": "Álex Pina"}], "number_of_seasons": 1,
    "vote_average": 8.2, "vote_count": 19000, "first_air_date": "2017-05-02",
    "aggregate_credits": {"cast": [{"name": "Úrsula Corberó"}]},
    "content_ratings": {"results": [{"iso_3166_1": "ES", "rating": "16"}]},
}


class ClienteFalso:
    def __init__(self, paginas=1):
        self.paginas = paginas

    def get(self, ruta, **parametros):
        if ruta.startswith("/discover"):
            pagina = parametros["page"]
            return {"results": [{"id": pagina * 100 + n} for n in range(3)] + [{"id": 100}],
                    "total_pages": self.paginas}
        return {"/movie/10": PELICULA, "/tv/20": SERIE}.get(ruta)


class TestDescarga(unittest.TestCase):
    def test_ficha_pelicula(self):
        f = ficha_pelicula(ClienteFalso(), 10, "ES")
        self.assertEqual(f["title"], "La deriva")
        self.assertEqual(f["director"], "Eva Stone")
        self.assertEqual(f["rating"], "12")  # la clasificación de España, no la de EE. UU.
        self.assertEqual(f["genres"], "Drama, Ciencia ficción")
        self.assertEqual(len(f["cast"].split(", ")), 8)
        self.assertEqual((f["release_year"], f["duration"]), ("2020", "120 min"))
        self.assertEqual(f["keywords"], "space, astronaut")
        self.assertEqual((f["poster"], f["backdrop"], f["popularity"]), ("/cartel.jpg", "", 12.35))
        self.assertEqual(f["english_title"], "Space Drift")  # prefiere la traducción de EE. UU.
        self.assertEqual(f["description"], "Astronautas en órbita.")  # la española no se toca

    def test_ficha_serie_usa_creadores_y_pais_de_origen(self):
        f = ficha_serie(ClienteFalso(), 20, "ES")
        # Título en coreano y sin sinopsis en castellano: se usa la versión inglesa.
        self.assertEqual(f["title"], "Squid Game")
        self.assertEqual(f["original_title"], "오징어 게임")
        self.assertEqual(f["description"], "A deadly game.")
        self.assertEqual(f["keywords"], "survival, game")
        self.assertEqual(f["director"], "Álex Pina")
        self.assertEqual(f["country"], "ES")
        self.assertEqual(f["content_type"], "TV Show")
        self.assertEqual(f["duration"], "1 temporada")

    def test_alfabeto_latino(self):
        self.assertTrue(es_alfabeto_latino("Miércoles"))
        self.assertTrue(es_alfabeto_latino("Ñu: año 2"))
        self.assertFalse(es_alfabeto_latino("ハイエナ"))
        self.assertFalse(es_alfabeto_latino("มหาลัยคลั่ง"))

    def test_ficha_inexistente(self):
        self.assertIsNone(ficha_pelicula(ClienteFalso(), 999, "ES"))

    def test_recorre_todas_las_paginas_sin_duplicados(self):
        ids = ids_en_netflix(ClienteFalso(paginas=3), "movie", "ES")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 9)  # 3 páginas × 3 ids; el 100 repetido cuenta una vez


if __name__ == "__main__":
    unittest.main()
