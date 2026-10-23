import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import bot


class BotFacturasTests(unittest.TestCase):
    def tearDown(self):
        for chat_id in list(bot.fotos_factura):
            bot._limpiar_foto_factura(chat_id)
        bot.esperando_foto_factura.clear()
        bot.confirmaciones_factura.clear()

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

        bot.solicitar_confirmacion_factura(15, productos)

        self.assertEqual(bot.confirmaciones_factura[15]["message_id"], 42)
        self.assertEqual(bot.confirmaciones_factura[15]["ingredientes"], productos)
        self.assertIn("✅ Confirmar", str(responder.call_args))

    @patch("bot.editar")
    @patch("bot.texto_alacena", return_value="🥫 En la alacena hay Papa")
    @patch("bot.compras.sumar_al_stock")
    def test_confirmar_suma_stock_y_cierra_confirmacion(self, sumar, texto, editar):
        productos = [("Papa", 2.0, "kg")]
        bot.confirmaciones_factura[15] = {"message_id": 42, "ingredientes": productos}

        bot.atender_boton_de_factura(15, 42, "factura:confirmar")

        sumar.assert_called_once_with(productos)
        self.assertNotIn(15, bot.confirmaciones_factura)
        editar.assert_called_once_with(15, 42, "✅ Compra confirmada.\n\n🥫 En la alacena hay Papa")

    @patch("bot.responder")
    @patch("bot.descargar_foto_telegram", return_value=Path("/tmp/factura_test.jpg"))
    def test_recibe_foto_solo_si_esta_esperandola(self, descargar, responder):
        bot.esperando_foto_factura.add(15)

        bot.atender_foto_factura(15, [{"file_id": "pequena"}, {"file_id": "grande", "file_size": 50}])

        descargar.assert_called_once_with("grande")
        self.assertEqual(bot.fotos_factura[15], Path("/tmp/factura_test.jpg"))
        self.assertNotIn(15, bot.esperando_foto_factura)
        responder.assert_called_once()

    @patch("bot.atender_foto_factura")
    @patch("bot.es_del_chat_permitido", return_value=True)
    def test_dispatcher_deriva_foto_al_manejador(self, permitido, atender_foto):
        fotos = [{"file_id": "foto"}]
        actualizacion = {"message": {"chat": {"id": 15}, "photo": fotos}}

        bot.atender(actualizacion)

        atender_foto.assert_called_once_with(15, fotos)


if __name__ == "__main__":
    unittest.main()