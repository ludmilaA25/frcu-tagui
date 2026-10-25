"""Lee una foto de factura usando una IA web manejada con TagUI.

La sesion de la IA debe estar iniciada en el Chrome de TagUI. Los selectores
dependen del proveedor y se configuran en CONFIG_IA o con variables de entorno.
"""

import argparse
import os
import platform
import sys
from pathlib import Path

import rpa as r

SELECTORES_ENVIAR = (
    '//button[contains(@aria-label,"Enviar") or contains(@aria-label,"Send")]',
    '//button[contains(@class,"send-button")]',
    '//button[.//mat-icon[contains(@data-mat-icon-name,"send")]]',
    '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[4]/div/div[2]/gem-icon-button/button/gem-icon/mat-icon',
    '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[3]/div/div[2]/gem-icon-button/button',
)


CONFIG_IA = {
    "url": "https://gemini.google.com",
    "selector_archivo": "images-files-uploader input[type='file']",
    "selector_adjunto": '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[2]/simplified-input-menu/div/span/gem-icon-button/button',
    "selector_opcion_subir": '//*[starts-with(@id,"cdk-overlay-")]/mat-card/mat-action-list/div[1]/uploader/div/div/div[1]/images-files-uploader/gem-button/button',
    "selector_prompt": '//input-area-v2//rich-textarea//*[@contenteditable="true"]',
    "selector_respuesta": "//model-response[last()]",
    "tiempo_maximo": "180",
}

VARIABLES_CONFIG = {
    "url": "FACTURA_IA_URL",
    "selector_archivo": "FACTURA_SELECTOR_ARCHIVO",
    "selector_adjunto": "FACTURA_SELECTOR_ADJUNTO",
    "selector_opcion_subir": "FACTURA_SELECTOR_OPCION_SUBIR",
    "selector_prompt": "FACTURA_SELECTOR_PROMPT",
    "selector_respuesta": "FACTURA_SELECTOR_RESPUESTA",
    "tiempo_maximo": "FACTURA_TIEMPO_MAXIMO",
}


class ErrorProcesadorFactura(Exception):
    """La automatizacion no pudo obtener una lectura de la factura."""


def _configuracion_actual():
    return {
        clave: os.environ.get(variable, CONFIG_IA[clave]).strip()
        for clave, variable in VARIABLES_CONFIG.items()
    }


def _validar_configuracion(config):
    faltantes = [
        clave for clave in (
            "url", "selector_adjunto", "selector_opcion_subir", "selector_prompt",
            "selector_respuesta"
        )
        if not config[clave]
    ]
    if faltantes:
        nombres = ", ".join(VARIABLES_CONFIG[clave] for clave in faltantes)
        raise ErrorProcesadorFactura(
            f"Falta configurar {nombres}. Los selectores dependen de la IA elegida."
        )
    try:
        if int(config["tiempo_maximo"]) < 1:
            raise ValueError
    except ValueError:
        raise ErrorProcesadorFactura("FACTURA_TIEMPO_MAXIMO tiene que ser un entero positivo.")


def construir_prompt(ingredientes_conocidos):
    """Arma una instruccion en una sola linea para que TagUI la escriba completa."""
    if isinstance(ingredientes_conocidos, dict):
        nombres = sorted({str(valor[0]) for valor in ingredientes_conocidos.values()})
    else:
        nombres = sorted({str(nombre) for nombre in ingredientes_conocidos})
    conocidos = ", ".join(nombres) if nombres else "ninguno"
    return (
        "Lee la foto adjunta. Responde EXCLUSIVAMENTE con una lista plana: un producto por "
        "renglon, en el formato exacto Ingrediente, cantidad, unidad. No agregues saludo, "
        "introduccion, titulo, explicaciones, Markdown, totales ni comentario de cierre. "
        "Ejemplo de formato: Papa, 1, kg. Unidades permitidas: kg, lt o unidad. "
        "Usa estos nombres existentes cuando correspondan: " + conocidos + ". "
        "Ignora precios e impuestos. No inventes datos; omite productos cuya cantidad o unidad "
        "no puedas determinar."
    )


def _iniciar_tagui():
    if platform.system() != "Linux":
        return r.init()

    openssl_conf = os.environ.get("OPENSSL_CONF")
    os.environ["OPENSSL_CONF"] = os.devnull
    try:
        return r.init()
    finally:
        if openssl_conf is None:
            os.environ.pop("OPENSSL_CONF", None)
        else:
            os.environ["OPENSSL_CONF"] = openssl_conf


def _esperar(selector, segundos):
    for _ in range(int(segundos)):
        if r.present(selector):
            return True
        r.wait(1)
    return r.present(selector)



def _clic_enviar():
    selector_configurado = os.environ.get("FACTURA_SELECTOR_ENVIAR", "").strip()
    selectores = ((selector_configurado,) if selector_configurado else ()) + SELECTORES_ENVIAR
    for selector in selectores:
        if _esperar(selector, 3) and r.click(selector):
            return True
    return False


def _leer_respuesta(selector):
    try:
        if not r.present(selector):
            return ""
        return r.read(selector).strip()
    except Exception:
        return ""


def _diagnosticar_adjunto():
    return r.dom(
        'return JSON.stringify({opciones:Array.from(document.querySelectorAll('
        '"[role=menuitem], [role=option], button, [role=button]"))'
        '.map(e=>({texto:(e.innerText||"").trim(),aria:e.getAttribute("aria-label"),'
        'titulo:e.getAttribute("title")}))'
        '.filter(e=>/upload|subir|archivo|file/i.test([e.texto,e.aria,e.titulo].join(" "))),'
        'archivos:Array.from(document.querySelectorAll("input[type=file]"))'
        '.map(e=>({accept:e.accept,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))})'
    )


def _esperar_respuesta_nueva(selector, respuesta_anterior, tiempo_maximo):
    respuesta = ""
    lecturas_iguales = 0
    for _ in range(tiempo_maximo):
        r.wait(1)
        actual = _leer_respuesta(selector)
        if actual and actual != respuesta_anterior:
            if actual == respuesta:
                lecturas_iguales += 1
            else:
                respuesta = actual
                lecturas_iguales = 0
            if lecturas_iguales >= 3:
                return respuesta
    raise ErrorProcesadorFactura(
        "La IA no devolvio una respuesta nueva y estable dentro del tiempo maximo."
    )


def procesar_factura(ruta_factura, ingredientes_conocidos):
    """Sube la factura a la IA web y devuelve su respuesta como texto.

    `ingredientes_conocidos` puede ser el diccionario que devuelve
    compras.ingredientes_conocidos() o una lista de nombres.
    """
    ruta = Path(ruta_factura).expanduser().resolve()
    if not ruta.is_file():
        raise ErrorProcesadorFactura(f"No existe el archivo de factura: {ruta}")

    config = _configuracion_actual()
    _validar_configuracion(config)
    tiempo_maximo = int(config["tiempo_maximo"])
    if not _iniciar_tagui():
        raise ErrorProcesadorFactura("No se pudo iniciar TagUI ni abrir Chrome.")

    try:
        r.url(config["url"])
        if not _esperar(config["selector_prompt"], tiempo_maximo):
            raise ErrorProcesadorFactura(
                "No encontre la caja de consulta. Inicia sesion en la IA en Chrome "
                "y revisa los selectores configurados."
            )

        if not _esperar(config["selector_adjunto"], 10):
            raise ErrorProcesadorFactura(
                "No encontre el boton de adjuntar en Gemini. Revisa FACTURA_SELECTOR_ADJUNTO."
            )
        r.click(config["selector_adjunto"])
        if not _esperar(config["selector_archivo"], 2):
            if not _esperar(config["selector_opcion_subir"], 8):
                diagnostico = _diagnosticar_adjunto()
                raise ErrorProcesadorFactura(
                    "No encontre la opcion de subir archivos. Elementos relacionados "
                    f"detectados en Gemini: {diagnostico}"
                )
            r.click(config["selector_opcion_subir"])

        if not _esperar(config["selector_archivo"], 10):
            raise ErrorProcesadorFactura(
                "No encontre el control para adjuntar archivos. Revisa FACTURA_SELECTOR_ARCHIVO."
            )

        respuesta_anterior = _leer_respuesta(config["selector_respuesta"])
        if not r.upload(config["selector_archivo"], str(ruta)):
            raise ErrorProcesadorFactura(
                "TagUI no pudo adjuntar la imagen; no voy a enviar el prompt sin la factura."
            )
        r.wait(8)
        if not _esperar(config["selector_prompt"], 30):
            raise ErrorProcesadorFactura(
                "La foto se adjunto, pero Gemini no volvio a mostrar la caja de consulta. "
                "No escribi ni envie el prompt."
            )
        if not r.click(config["selector_prompt"]):
            raise ErrorProcesadorFactura("No pude enfocar la caja de consulta.")
        if not r.type(config["selector_prompt"], construir_prompt(ingredientes_conocidos)):
            raise ErrorProcesadorFactura(
                "No pude escribir el prompt; la consulta no se envio. Revisa el selector de la caja."
            )
        if not _clic_enviar():
            raise ErrorProcesadorFactura(
                "Escribi el prompt, pero no encontre ninguno de los botones Enviar configurados. "
                "La consulta no se envio."
            )
        return _esperar_respuesta_nueva(
            config["selector_respuesta"], respuesta_anterior, tiempo_maximo
        )
    finally:
        r.close()


def _argumentos_cli():
    parser = argparse.ArgumentParser(
        description="Procesa manualmente una foto de factura con la IA web configurada."
    )
    parser.add_argument("foto", type=Path, help="Ruta a la foto de la factura")
    parser.add_argument(
        "--subir",
        action="store_true",
        help="Confirma que la foto se enviara al servicio externo de IA configurado.",
    )
    return parser.parse_args()


def main():
    args = _argumentos_cli()
    if not args.subir:
        raise SystemExit(
            "La foto se subira a un servicio externo de IA. Revisa la privacidad del ticket "
            "y vuelve a ejecutar agregando --subir si estas de acuerdo."
        )

    try:
        import compras

        respuesta = procesar_factura(args.foto, compras.ingredientes_conocidos())
    except ErrorProcesadorFactura as error:
        print(f"FALLO: {error}", file=sys.stderr)
        raise SystemExit(2)
    print(respuesta)


if __name__ == "__main__":
    main()