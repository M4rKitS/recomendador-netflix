import unittest
from pathlib import Path

from recomendador import Recomendador, normalizar, palabras_clave, puntuacion, separar_lista

CSV = Path(__file__).parent / "datos_prueba.csv"


class TestLimpieza(unittest.TestCase):
    def test_normalizar_quita_acentos_y_signos(self):
        self.assertEqual(normalizar("Pedro Almodóvar!"), "pedro almodovar")

    def test_separar_lista(self):
        self.assertEqual(separar_lista("Dramas,  Comedies ,"), ["dramas", "comedies"])
        self.assertEqual(separar_lista(float("nan")), [])

    def test_palabras_clave_sin_stopwords_y_con_raiz(self):
        palabras = palabras_clave("The astronauts are fighting", "english")
        self.assertIn("astronaut", palabras)
        self.assertIn("fight", palabras)
        self.assertNotIn("the", palabras)

    def test_palabras_clave_en_castellano(self):
        palabras = palabras_clave("Unos astronautas luchan por volver a la Tierra")
        self.assertIn("astronaut", palabras)
        self.assertNotIn("por", palabras)

    def test_puntuacion(self):
        self.assertEqual(puntuacion("6.6/10"), 6.6)


class TestRecomendador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motor = Recomendador.desde_csv(CSV)

    def test_la_secuela_es_la_primera_recomendacion(self):
        self.assertEqual(self.motor.recomendar("Space Drift")[0].titulo, "Space Drift 2")
        self.assertEqual(self.motor.recomendar("cartel kings")[0].titulo, "Cartel Kings: Mexico")

    def test_no_se_recomienda_a_si_mismo(self):
        titulos = [r.titulo for r in self.motor.recomendar("Space Drift", cantidad=10)]
        self.assertNotIn("Space Drift", titulos)

    def test_filtro_por_tipo(self):
        recs = self.motor.recomendar("Almodóvar Nights", tipo="Movie")
        self.assertTrue(recs)
        self.assertTrue(all(r.tipo == "Movie" for r in recs))

    def test_explica_las_coincidencias(self):
        rec = self.motor.recomendar("Space Drift")[0]
        self.assertEqual(rec.coincidencias["director"], ["Eva Stone"])
        self.assertIn("Tom Hale", rec.coincidencias["reparto"])

    def test_titulo_inexistente(self):
        with self.assertRaises(KeyError):
            self.motor.recomendar("No existe")

    def test_buscador_con_acentos(self):
        self.assertEqual(self.motor.buscar_titulos("almodovar"), ["Almodóvar Nights"])
        self.assertEqual(self.motor.buscar_titulos("space")[0], "Space Drift")


if __name__ == "__main__":
    unittest.main()


class TestCatalogoTMDb(unittest.TestCase):
    """CSV con el formato que genera descargar_catalogo.py (en castellano)."""

    @classmethod
    def setUpClass(cls):
        cls.motor = Recomendador.desde_csv(Path(__file__).parent / "catalogo_prueba_tmdb.csv")

    def test_detecta_castellano(self):
        self.assertEqual(self.motor.idioma, "spanish")

    def test_busca_por_titulo_original(self):
        self.assertEqual(self.motor.buscar_titulos("the big heist")[0], "El gran golpe")
        self.assertEqual(self.motor.recomendar("The Big Heist")[0].titulo, "El gran golpe: Berlín")

    def test_busca_por_titulo_ingles_y_explica_temas(self):
        self.assertEqual(self.motor.buscar_titulos("big heist: ber")[0], "El gran golpe: Berlín")
        rec = self.motor.recomendar("El gran golpe")[0]
        self.assertEqual(rec.coincidencias["temas"], ["heist"])
        # El tema "spain" no debe pisar cómo se escribe el país "Spain".
        self.assertEqual(rec.coincidencias["pais"], ["Spain"])

    def test_sinopsis_en_ingles_dentro_de_un_catalogo_en_castellano(self):
        i = self.motor.indice_de("Squid Game")
        self.assertIn("player", self.motor.etiquetas[i]["palabras_clave"])  # raíz inglesa, no española

    def test_titulos_repetidos_llevan_el_anio(self):
        titulos = set(self.motor.datos["titulo"])
        self.assertIn("La deriva (2020)", titulos)
        self.assertIn("La deriva (2011)", titulos)
