import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compras


class SumarStockTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()