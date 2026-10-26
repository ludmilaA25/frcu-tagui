import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import bot
import configuracion
import requests


class BotFacturasTests(unittest.TestCase):
    def tearDown(self):
        for chat_id in list(bot.fotos_factura):
            bot._limpiar_foto_factura(chat_id)
        bot.esperando_foto_factura.clear()
        bot.confirmaciones_factura.clear()
        bot.menus.clear()

    @patch("configuracion.leer_config", return_value={})
    def test_configuracion_factura_usa_defaults_y_override_de_timeout(self, leer_config):
        with patch.dict(os.environ, {"FACTURA_TIMEOUT_SECONDS": "45"}, clear=True):
            config = configuracion.leer_configuracion_factura()

        self.assertEqual(config["url"], "https://gemini.google.com")
        self.assertEqual(config["tiempo_maximo"], "45")
        self.assertEqual(config["selector_archivo"], "images-files-uploader input[type='file']")
        self.assertEqual(config["selectores_enviar"], configuracion.FACTURA_SELECTORES_ENVIAR)

    def test_archiva_foto_en_directorio_de_evidencia(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = Path(carpeta) / "entrada.jpeg"
            origen.write_bytes(b"ticket de prueba")
            destino_evidencia = Path(carpeta) / "evidencia"

            with patch.object(bot, "CARPETA_EVIDENCIA_FACTURAS", destino_evidencia):
                archivada = bot.archivar_foto_factura(origen)

            self.assertEqual(archivada.read_bytes(), b"ticket de prueba")
            self.assertTrue(archivada.name.startswith("ticket_"))
            self.assertEqual(archivada.suffix, ".jpeg")

    @patch("bot.responder")
    @patch("bot.archivar_foto_factura", return_value=Path("/tmp/factura_evidencia.jpg"))
    @patch("bot.procesador_factura.procesar_factura", side_effect=Exception("timeout interno"))
    @patch("bot.descargar_foto_telegram", return_value=Path("/tmp/ticket.jpg"))
    def test_lector_tiene_timeout_global_de_60_segundos(self, descargar, procesar, archivar, responder):
        """Si procesador_factura falla (por ej. timeout interno), se ofrece Plan B."""
        bot.esperando_foto_factura.add(15)
        responder.side_effect = [{"ok": True}, {"ok": True}]

        bot.atender_foto_factura(15, [{"file_id": "foto"}])

        procesar.assert_called_once()
        botones = responder.call_args_list[1].args[2]
        callback_data = [boton["callback_data"] for fila in botones for boton in fila]
        self.assertIn("factura:manual", callback_data)

    def test_consulta_muestra_faltantes_de_receta_en_chat_del_bot(self):
        bot.menus[(15, 42)] = {"modo": "recetas", "comida_actual": "Tarta"}
        consulta = {
            "id": "callback",
            "data": "receta:disponibilidad",
            "message": {"chat": {"id": 15}, "message_id": 42},
        }

        with patch("bot.llamar") as llamar, \
             patch("bot.editar") as editar, \
             patch("bot.compras.comidas_disponibles", return_value=["Tarta"]), \
             patch(
                 "bot.compras.faltantes_para_receta",
                 return_value=[("Huevo", 4, "unidad"), ("Leche", 1, "lt")],
             ):
            bot.atender_boton(consulta)

        llamar.assert_called_once_with("answerCallbackQuery", callback_query_id="callback")
        editar.assert_called_once()
        self.assertEqual(editar.call_args.args[0:2], (15, 42))
        self.assertIn("Para Tarta te falta:", editar.call_args.args[2])
        self.assertIn("Huevo: 4 unidad", editar.call_args.args[2])
        self.assertIn("Leche: 1 lt", editar.call_args.args[2])

    def test_consulta_indica_si_hay_todos_los_ingredientes(self):
        bot.menus[(15, 42)] = {"modo": "recetas", "comida_actual": "Tarta"}
        consulta = {
            "id": "callback",
            "data": "receta:disponibilidad",
            "message": {"chat": {"id": 15}, "message_id": 42},
        }

        with patch("bot.llamar"), \
             patch("bot.editar") as editar, \
             patch("bot.compras.comidas_disponibles", return_value=["Tarta"]), \
             patch("bot.compras.faltantes_para_receta", return_value=[]):
            bot.atender_boton(consulta)

        self.assertIn("Tenés todos los ingredientes", editar.call_args.args[2])

    @patch("bot.responder")
    @patch("bot.descargar_foto_telegram", side_effect=requests.RequestException("sin red"))
    def test_fallo_descarga_ofrece_plan_b_manual(self, descargar, responder):
        bot.esperando_foto_factura.add(15)

        bot.atender_foto_factura(15, [{"file_id": "foto"}])

        botones = responder.call_args.args[2]
        callback_data = [boton["callback_data"] for fila in botones for boton in fila]
        self.assertIn("factura:manual", callback_data)

    @patch("bot.requests.get")
    @patch("bot.llamar", return_value={"ok": True, "result": {"file_path": "photos/file_0.jpg"}})
    def test_descarga_usa_el_endpoint_de_archivos_de_telegram(self, llamar, get):
        respuesta = Mock()
        respuesta.content = b"contenido de prueba"
        get.return_value = respuesta

        with patch.object(bot, "API_ARCHIVOS", "https://api.telegram.org/file/botTOKEN/"):
            ruta = bot.descargar_foto_telegram("file-id")
        self.addCleanup(ruta.unlink, missing_ok=True)

        llamar.assert_called_once_with("getFile", file_id="file-id")
        get.assert_called_once_with(
            "https://api.telegram.org/file/botTOKEN/photos/file_0.jpg", timeout=60
        )
        self.assertEqual(ruta.read_bytes(), b"contenido de prueba")

    @patch("bot.responder", return_value={"ok": True, "result": {"message_id": 42}})
    def test_solicita_confirmacion_y_guarda_estado(self, responder):
        productos = [("Papa", 2.0, "kg")]

        with patch("bot.compras.stock_proyectado_de_compra", return_value=productos):
            bot.solicitar_confirmacion_factura(15, productos)

        self.assertEqual(bot.confirmaciones_factura[15]["message_id"], 42)
        self.assertEqual(bot.confirmaciones_factura[15]["ingredientes"], productos)
        self.assertEqual(bot.confirmaciones_factura[15]["stock_proyectado"], productos)
        self.assertIn("✅ Confirmar", str(responder.call_args))
        self.assertIn("Papa, 2, kg", responder.call_args.args[1])

    @patch("bot.editar")
    @patch("bot.texto_alacena", return_value="🥫 En la alacena hay Papa")
    @patch("bot.compras.sumar_al_stock")
    def test_confirmar_suma_stock_y_cierra_confirmacion(self, sumar, texto, editar):
        productos = [("Papa", 2.0, "kg")]
        bot.confirmaciones_factura[15] = {
            "message_id": 42,
            "ingredientes": productos,
            "stock_proyectado": [("Papa", 4.0, "kg")],
        }

        bot.atender_boton_de_factura(15, 42, "factura:confirmar")

        sumar.assert_called_once_with(productos)
        self.assertNotIn(15, bot.confirmaciones_factura)
        editar.assert_called_once_with(
            15,
            42,
            "✅ Compra confirmada.\n\n🥫 En la alacena hay Papa",
            [[{"text": "🏠 Volver al menú", "callback_data": "factura:menu"}]],
        )

    @patch("bot.responder")
    @patch("bot.procesador_factura.procesar_factura", return_value="Papa, 2, kg\nLista detectada:")
    @patch("bot.descargar_foto_telegram", return_value=Path("/tmp/factura_test.jpg"))
    @patch("bot.archivar_foto_factura", return_value=Path("/tmp/factura_evidencia.jpg"))
    @patch("bot.compras.stock_proyectado_de_compra", return_value=[("Papa", 6.0, "kg")])
    def test_recibe_foto_y_muestra_resultado_para_confirmar(
        self, proyectado, archivar, descargar, procesar, responder
    ):
        bot.esperando_foto_factura.add(15)
        responder.side_effect = [
            {"ok": True},
            {"ok": True, "result": {"message_id": 43}},
        ]

        bot.atender_foto_factura(15, [{"file_id": "pequena"}, {"file_id": "grande", "file_size": 50}])

        descargar.assert_called_once_with("grande")
        procesar.assert_called_once()
        archivar.assert_called_once_with(Path("/tmp/factura_test.jpg"))
        self.assertEqual(bot.fotos_factura[15], Path("/tmp/factura_test.jpg"))
        self.assertNotIn(15, bot.esperando_foto_factura)
        self.assertEqual(bot.confirmaciones_factura[15]["ingredientes"], [("Papa", 2.0, "kg")])
        vista_previa = responder.call_args_list[1].args[1]
        self.assertIn("Papa, 6, kg", vista_previa)
        self.assertNotIn("Omití", vista_previa)
        self.assertNotIn("Lista detectada:", vista_previa)
        self.assertNotIn("Lista detectada:", str(bot.confirmaciones_factura[15]["ingredientes"]))

    @patch("bot.atender_foto_factura")
    @patch("bot.es_del_chat_permitido", return_value=True)
    def test_dispatcher_deriva_foto_al_manejador(self, permitido, atender_foto):
        fotos = [{"file_id": "foto"}]
        actualizacion = {"message": {"chat": {"id": 15}, "photo": fotos}}

        bot.atender(actualizacion)

        atender_foto.assert_called_once_with(15, fotos)

    def test_consulta_muestra_faltantes_de_receta(self):
        bot.menus[(15, 42)] = {"modo": "recetas", "comida_actual": "Tarta"}
        consulta = {
            "id": "callback",
            "data": "receta:disponibilidad",
            "message": {"chat": {"id": 15}, "message_id": 42},
        }
        with patch("bot.llamar"), \
             patch("bot.editar") as editar, \
             patch("bot.compras.comidas_disponibles", return_value=["Tarta"]), \
             patch(
                 "bot.compras.faltantes_para_receta",
                 return_value=[("Huevo", 4, "unidad"), ("Leche", 1, "lt")],
             ):
            bot.atender_boton(consulta)

        texto = editar.call_args.args[2]
        self.assertIn("Para Tarta te falta:", texto)
        self.assertIn("Huevo: 4 unidad", texto)
        self.assertIn("Leche: 1 lt", texto)

    @patch("bot.responder")
    @patch("bot.archivar_foto_factura", return_value=Path("/tmp/factura_evidencia.jpg"))
    @patch("bot.procesador_factura.procesar_factura", side_effect=Exception("fallo de Gemini"))
    @patch("bot.descargar_foto_telegram", return_value=Path("/tmp/factura_fallback_test.jpg"))
    def test_falla_lector_ofrece_carga_manual(self, descargar, procesar, archivar, responder):
        bot.esperando_foto_factura.add(15)
        responder.side_effect = [{"ok": True}, {"ok": True}]

        bot.atender_foto_factura(15, [{"file_id": "foto"}])

        botones = responder.call_args_list[1].args[2]
        callback_data = [boton["callback_data"] for fila in botones for boton in fila]
        self.assertIn("factura:manual", callback_data)


if __name__ == "__main__":
    unittest.main()