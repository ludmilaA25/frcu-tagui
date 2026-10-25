import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compras


class SumarStockTests(unittest.TestCase):
    def test_stock_proyectado_suma_docena_sin_modificar_alacena(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "StockActual.csv"
            ruta.write_text(
                "Ingrediente,CantidadDisponible,Unidad\nHuevo,4,unidad\n",
                encoding="utf-8",
            )
            (Path(carpeta) / "BaseDatos.csv").write_text(
                "Comida,Ingrediente,Cantidad,Unidad\nTortilla,Huevo,2,unidad\n",
                encoding="utf-8",
            )
            with patch.object(compras, "CARPETA_DATOS", Path(carpeta)):
                vista_previa = compras.stock_proyectado_de_compra(
                    [("Huevo", 12, "unidad")]
                )
                stock_sin_confirmar = compras.stock_actual()

        self.assertEqual(vista_previa, [("Huevo", 16.0, "unidad")])
        self.assertEqual(stock_sin_confirmar, [("Huevo", "4", "unidad")])

    def test_suma_compra_al_stock_existente_y_agrega_productos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "StockActual.csv"
            ruta.write_text(
                "Ingrediente,CantidadDisponible,Unidad\nPapa,1,kg\n",
                encoding="utf-8",
            )
            (Path(carpeta) / "BaseDatos.csv").write_text(
                "Comida,Ingrediente,Cantidad,Unidad\nTortilla,Papa,1,kg\n"
                "Tortilla,Leche,1,lt\n",
                encoding="utf-8",
            )
            with patch.object(compras, "CARPETA_DATOS", Path(carpeta)):
                compras.sumar_al_stock([("Papa", 2.5, "kg"), ("Leche", 1, "lt")])
                resultado = compras.stock_actual()

        self.assertEqual(resultado, [("Papa", "3.5", "kg"), ("Leche", "1", "lt")])

    def test_no_suma_unidades_incompatibles(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "StockActual.csv"
            ruta.write_text(
                "Ingrediente,CantidadDisponible,Unidad\nPapa,1,kg\n",
                encoding="utf-8",
            )
            (Path(carpeta) / "BaseDatos.csv").write_text(
                "Comida,Ingrediente,Cantidad,Unidad\nTortilla,Papa,1,kg\n",
                encoding="utf-8",
            )
            with patch.object(compras, "CARPETA_DATOS", Path(carpeta)):
                with self.assertRaises(compras.ErrorDeDatos):
                    compras.sumar_al_stock([("Papa", 1, "lt")])


class InterpretarFacturaTests(unittest.TestCase):
    def test_respuesta_de_captura_conserva_solo_unidades_compatibles(self):
        respuesta = (
            "Gemini ha dicho1 unidad Arroz\n"
            "1 unidad Queso rallado\n"
            "1 unidad Tapas de empanada\n"
            "0,385 kg Queso mozzarella\n"
            "0,690 kg Limon"
        )
        conocidos = {
            "arroz": ("Arroz", "kg"),
            "queso rallado": ("Queso rallado", "kg"),
            "tapas de empanada": ("Tapas de empanada", "unidad"),
            "queso mozzarella": ("Queso mozzarella", "kg"),
            "limon": ("Limon", "unidad"),
        }

        with patch("compras.ingredientes_conocidos", return_value=conocidos):
            ingredientes, rechazados = compras.interpretar_respuesta_factura(respuesta)

        self.assertEqual(
            ingredientes,
            [
                ("Tapas de empanada", 1.0, "unidad"),
                ("Queso mozzarella", 0.385, "kg"),
            ],
        )
        self.assertEqual(len(rechazados), 3)
        self.assertNotIn("Gemini", str(ingredientes))

    def test_normaliza_respuesta_gemini_con_cantidad_primero_y_prefijo(self):
        respuesta = (
            "Gemini ha dicho1 unidad Arroz\n"
            "1 unidad Queso rallado\n"
            "1 unidad Tapas de empanada\n"
            "0,385 kg Queso mozzarella\n"
            "0,690 kg Limon"
        )

        with patch("compras.ingredientes_conocidos", return_value={}):
            ingredientes, rechazados = compras.interpretar_respuesta_factura(respuesta)

        self.assertEqual(
            ingredientes,
            [
                ("Arroz", 1.0, "unidad"),
                ("Queso rallado", 1.0, "unidad"),
                ("Tapas de empanada", 1.0, "unidad"),
                ("Queso mozzarella", 0.385, "kg"),
                ("Limon", 0.69, "kg"),
            ],
        )
        self.assertEqual(rechazados, [])

    def test_separa_ingredientes_validos_de_texto_no_interpretable(self):
        respuesta = (
            "Aquí está la lista:\n"
            "- Papa, 0,5, kg\n"
            "Leche, 1, lt\n"
            "Espero que te sirva."
        )

        ingredientes, rechazados = compras.interpretar_respuesta_factura(respuesta)

        self.assertEqual(ingredientes, [("Papa", 0.5, "kg"), ("Leche", 1.0, "lt")])
        self.assertEqual(rechazados, ["Aquí está la lista:", "Espero que te sirva."])


if __name__ == "__main__":
    unittest.main()