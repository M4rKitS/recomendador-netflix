import tempfile
import unittest
from pathlib import Path

from comprobar_catalogo import problema, titulos_anteriores


class TestComprobarCatalogo(unittest.TestCase):
    def test_catalogo_normal(self):
        self.assertIsNone(problema(9900, 9886))

    def test_pequenas_bajadas_son_normales(self):
        self.assertIsNone(problema(9500, 9886))  # -3,9 %

    def test_bajada_brusca_no_se_publica(self):
        self.assertIn("738 menos", problema(9073, 9811))  # lo que pasó el 27/11/2026

    def test_catalogo_demasiado_pequeno(self):
        self.assertIn("mínimo", problema(1200, None))

    def test_sin_dato_anterior_solo_mira_el_minimo(self):
        self.assertIsNone(problema(6000, None))

    def test_lee_el_ultimo_numero_publicado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ULTIMA_ACTUALIZACION.md"
            ruta.write_text("Última actualización del catálogo: 2026-11-26 (9886 títulos).\n", encoding="utf-8")
            self.assertEqual(titulos_anteriores(ruta), 9886)
            self.assertIsNone(titulos_anteriores(Path(carpeta) / "no-existe.md"))

    def test_lee_cada_pais_por_separado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ULTIMA_ACTUALIZACION.md"
            ruta.write_text("Última actualización del catálogo: 2026-12-01.\n\n"
                            "- Netflix España: 9850 títulos.\n- Netflix USA: 7123 títulos.\n", encoding="utf-8")
            self.assertEqual(titulos_anteriores(ruta, "ES"), 9850)
            self.assertEqual(titulos_anteriores(ruta, "US"), 7123)

    def test_pais_nuevo_sin_dato_anterior(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ULTIMA_ACTUALIZACION.md"
            ruta.write_text("Última actualización del catálogo: 2026-11-27 (9110 títulos).\n", encoding="utf-8")
            self.assertEqual(titulos_anteriores(ruta, "ES"), 9110)
            self.assertIsNone(titulos_anteriores(ruta, "US"))


if __name__ == "__main__":
    unittest.main()
