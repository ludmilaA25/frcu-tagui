import unittest
from pathlib import Path
from unittest.mock import patch

import procesamiento


class ProcesarPedidoTests(unittest.TestCase):
    @patch("procesamiento._ejecutar_robot")
    @patch("procesamiento.compras.guardar_evidencia")
    @patch("procesamiento.compras.calcular_lista", return_value=([], ["Comida sin receta"]))
    def test_sin_faltantes_no_ejecuta_el_robot(self, calcular, guardar, ejecutar):
        resultado = procesamiento.procesar_pedido(["Comida"], "Grupo")

        self.assertEqual(resultado.faltantes, [])
        self.assertEqual(resultado.advertencias, ["Comida sin receta"])
        guardar.assert_not_called()
        ejecutar.assert_not_called()

    @patch("procesamiento._ejecutar_robot", return_value=Path("captura.png"))
    @patch("procesamiento.compras.guardar_evidencia")
    @patch("procesamiento.compras.armar_mensaje", return_value="Comprar Papa")
    @patch("procesamiento.compras.calcular_lista", return_value=([("Papa", 1, "kg")], []))
    def test_con_faltantes_guarda_evidencia_y_devuelve_captura(
        self, calcular, armar, guardar, ejecutar
    ):
        resultado = procesamiento.procesar_pedido(["Comida"], "Grupo")

        self.assertEqual(resultado.mensaje, "Comprar Papa")
        self.assertEqual(resultado.captura, Path("captura.png"))
        guardar.assert_called_once_with("Comprar Papa")
        ejecutar.assert_called_once_with("Comprar Papa", "Grupo")

    @patch(
        "procesamiento._ejecutar_robot",
        side_effect=procesamiento.ErrorDeEjecucion("Telegram Web no disponible"),
    )
    @patch("procesamiento.compras.guardar_evidencia")
    @patch("procesamiento.compras.armar_mensaje", return_value="Comprar Papa")
    @patch("procesamiento.compras.calcular_lista", return_value=([("Papa", 1, "kg")], []))
    def test_falla_del_robot_devuelve_mensaje_para_respaldo(
        self, calcular, armar, guardar, ejecutar
    ):
        resultado = procesamiento.procesar_pedido(["Comida"], "Grupo")

        self.assertEqual(resultado.mensaje, "Comprar Papa")
        self.assertEqual(resultado.error_robot, "Telegram Web no disponible")
        self.assertIsNone(resultado.captura)


if __name__ == "__main__":
    unittest.main()