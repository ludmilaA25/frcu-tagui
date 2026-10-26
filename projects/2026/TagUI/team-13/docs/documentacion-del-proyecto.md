# Documentación del proyecto — TPI RPA Grupo 13

Este documento responde, punto por punto, a lo que pide la consigna del Trabajo Práctico
Integrador (Etapa 1, grupos de RPA). Está pensado para que el grupo que reciba este
proyecto en la Etapa 2 entienda **qué se automatizó, por qué se hizo así y por dónde
seguir**, sin tener que preguntarnos.

| Punto de la consigna | Dónde está |
|---|---|
| 1. Selección de la herramienta RPA | [Sección 1](#1-herramienta-rpa-seleccionada) |
| 2. Selección y validación del proceso | [Sección 2](#2-selección-y-validación-del-proceso) |
| 3. Definición del proceso a automatizar | [Sección 3](#3-definición-del-proceso-a-automatizar) |
| 4. Implementación | El código en `Ejecutables/`, explicado en [`explicaciones-archivos/`](explicaciones-archivos/) y resumido en la [sección 4](#4-implementación) |
| 5. Tres conceptos teóricos | [Sección 5](#5-conceptos-teóricos-aplicados) |
| 6. Instructivo de instalación | [`instructivo-instalacion.md`](instructivo-instalacion.md) (y el de uso: [`instructivo-uso.md`](instructivo-uso.md)) |
| 7. Posible mejora para la Etapa 2 | [Sección 7](#7-mejora-propuesta-para-la-etapa-2-cargar-la-factura-con-una-foto) |
| Presentación: cronología, contratiempos y riesgos | [Sección 6](#6-cronología-contratiempos-y-riesgos) |

---

## 1. Herramienta RPA seleccionada

**TagUI**, manejada desde **Python** con la librería **`rpa`** (RPA for Python).

### Características principales de TagUI

- Es **open source y gratuita**, desarrollada por AI Singapore (programa de la
  Universidad Nacional de Singapur).
- Es **multiplataforma**: funciona en Windows, Linux y macOS.
- Automatiza **navegadores web y aplicaciones de escritorio** imitando a una persona:
  hace clicks, escribe, lee lo que aparece en pantalla y saca capturas.
- Los flujos se escriben como **scripts de texto plano**, fáciles de leer.
- Se integra con **Python**: la librería `rpa`, del mismo autor, permite manejar TagUI
  desde un programa Python (`r.init()`, `r.url()`, `r.click()`, `r.type()`, `r.snap()`...).
  La primera vez descarga TagUI sola, con su propio Chrome.

### Por qué la elegimos

1. **Es la herramienta que se vio en profundidad en clase** (20/08), con un repositorio
   de ejemplos de la cátedra.
2. **Corre igual en Windows y en Linux.** Es un requisito fuerte para este trabajo: en la
   Etapa 2 el proyecto lo instala otro grupo, que tiene integrantes con Linux. Por eso
   descartamos **Power Automate Desktop**, que solo existe para Windows.
3. **Es gratuita** y no pide licencias ni cuentas, así que cualquiera la puede instalar
   siguiendo el instructivo.
4. **Manejarla desde Python** nos permitió escribir en el mismo lenguaje el bot de
   Telegram (el disparador), el cálculo y el robot. Además Python permite dividir el
   código en archivos que se importan entre sí, algo que los scripts `.tag` de TagUI no
   permiten. Así el código queda más ordenado y es más fácil de entender para quien lo
   reciba.

---

## 2. Selección y validación del proceso

- El **alcance original validado** con los docentes fue: calcular la lista de compras
  del **menú semanal completo** a partir de las recetas y de lo que hay en la alacena, y
  enviarla por Telegram.
- El **10/09** los docentes aclararon que el bot de Telegram solo cuenta como RPA si es
  el **disparador de un proceso local** que interactúe con la máquina como lo haría un
  usuario y devuelva un resultado. Por eso rediseñamos el proyecto: ahora el robot
  maneja Chrome y escribe la lista en Telegram Web, igual que una persona.
- **Ampliación del alcance:** a pedido del grupo se agregó elegir **una comida** o
  **varias comidas**, además del menú semanal. También se sumó ver y cargar recetas,
  cambiar o sortear el menú, y mantener la alacena desde el bot. El flujo semanal
  aprobado sigue intacto: lo nuevo es un agregado, no un reemplazo.

---

## 3. Definición del proceso a automatizar

### El proceso de negocio

En una casa, alguien tiene que decidir qué se va a cocinar, revisar qué ingredientes
lleva cada comida, fijarse qué hay en la alacena, calcular qué falta y mandarle la lista
al grupo de la familia para que quien vaya al súper sepa qué comprar.

Hecho a mano es un proceso **repetitivo, basado en reglas y propenso a errores**
(olvidarse de un ingrediente, no descontar lo que ya hay, sumar mal cuando una comida se
repite en la semana). Por eso es un buen candidato para RPA.

### Objetivo

Que la persona **solo tenga que elegir qué quiere cocinar** desde Telegram, y que el
sistema haga el resto: calcular qué falta comprar y **enviar la lista al grupo** desde la
cuenta de la persona, como lo haría ella misma.

### Alcance

**Incluye:**

- Pedir la lista para una comida, varias (con repeticiones) o el menú de la semana.
- Calcular qué falta: ingredientes de las recetas **menos** lo que hay en la alacena, con
  unidades y redondeos coherentes.
- Que un robot abra Telegram Web, busque el grupo, pegue la lista, la envíe y devuelva
  una captura como confirmación.
- Mantener los datos desde el bot: ver y cargar recetas, cambiar o sortear el menú y
  actualizar la alacena.
- Recibir una foto del ticket en el chat privado del bot, leerla con Gemini y actualizar
  la alacena **solo después de que la persona confirme** los totales.
- Consultar si una receta puede prepararse con el stock actual y mostrar qué cantidades
  faltan.

**No incluye:**

- Precios ni presupuesto.
- Registrar compras o consumos automáticamente sin una foto de ticket o una actualización
  manual de la persona.
- Envases o presentaciones: el sistema puede pedir "0.2 kg de pan rallado", aunque en
  el súper se compre un paquete.

### Restricciones de uso

**Al inicio** (para que funcione hoy):

- La PC tiene que estar **prendida y desbloqueada** mientras el bot atiende. Con la
  sesión bloqueada Chrome deja de dibujar las páginas, igual que le pasaría a una
  persona que no ve la pantalla.
- Hay que **iniciar sesión en Telegram Web una vez** (escaneando un QR), en el Chrome
  propio de TagUI.
- Hay que **iniciar sesión en Gemini** en ese mismo Chrome antes de cargar una factura.
- El ticket se sube a Gemini; no se deben enviar fotos con datos personales que no sean
  necesarios. Se conserva una copia local en `docs/evidencia/facturas/`, excluida de Git.
- Hay que armar `config.txt` con el token del bot, el chat autorizado y el nombre exacto
  del grupo.
- Solo se aceptan las unidades `kg`, `lt` y `unidad`.
- El bot **solo atiende a un chat**: el configurado en `config.txt`.
- Los datos que vienen cargados (recetas, stock y menú) son **de ejemplo**.

**A largo plazo** (lo que puede romperse o limitar el uso con el tiempo):

- **Dependencia del diseño de las páginas web:** si Telegram o Gemini cambian sus
  interfaces, el robot puede dejar de encontrar controles. Los selectores de Telegram
  están centralizados en `robot_telegram_web.py`; los de Gemini, en `configuracion.py`.
- **El stock depende de que la persona lo mantenga al día.** Si no lo actualiza, la lista
  pide cosas que ya hay, o no pide cosas que faltan.
- **Una sola PC y un solo usuario:** el bot corre en la PC de una persona y escribe
  desde su cuenta.
- **Versión fija de la librería** (`rpa==1.50.0` en `requirements.txt`), para que una
  actualización no cambie el comportamiento sin que nos demos cuenta.

### Controles implementados (para verificar que la automatización funciona bien)

| Control | Qué verifica | Dónde |
|---|---|---|
| Chat autorizado | Solo el chat de `config.txt` puede disparar el robot. Los pedidos de otros chats se ignoran. | `bot.py` → `es_del_chat_permitido` |
| Pedidos viejos descartados | Al prenderse, el bot ignora lo que llegó mientras estaba apagado, para que nada se dispare solo. | `bot.py` → `descartar_pendientes` |
| Validación de datos cargados | Cada renglón de receta o de alacena se revisa: formato, número, cantidad positiva y unidad válida. Si el ingrediente ya existe, tiene que ir con el mismo nombre y la misma unidad. | `compras.py` → `interpretar_ingrediente` |
| Validación de los CSV | Una cantidad que no es número en un CSV corta el cálculo con un mensaje que dice archivo y fila. | `compras.py` → `_a_numero` |
| Comida sin receta | Si el menú pide una comida que no tiene receta, se avisa y se calcula el resto. | `compras.py` → `calcular_lista` |
| Aviso de posible error de tipeo | Si se carga en la alacena algo que ninguna receta usa, se guarda pero se avisa. | `bot.py` → `atender_texto_de_alacena` |
| Búsqueda solo entre chats propios | El robot nunca elige un resultado de la búsqueda global de Telegram, para no escribirle a un desconocido con el mismo nombre. | `robot_telegram_web.py` → `_resultado_de_busqueda` |
| Verificación del pegado | Después de pegar, el robot lee la caja de mensaje y compara que diga exactamente la lista. | `robot_telegram_web.py` → `_pegar_mensaje` |
| Verificación del envío | Después de tocar "enviar", el robot espera a que la caja quede vacía, que es la señal de que el mensaje salió. | `robot_telegram_web.py` → `_enviar` |
| Tiempo máximo Telegram Web | Si el robot de envío tarda más de 3 minutos, se lo corta y el bot sigue atendiendo. | `bot.py` → `ejecutar_robot` |
| Plan B | Si el robot falla, el bot manda la lista él mismo por la Bot API, con el motivo. | `bot.py` → `cerrar_menu_y_procesar` |
| Evidencia | Cada corrida deja la lista en `mensaje.txt`, y el bot confirma con una captura de Telegram Web. | `compras.py` → `guardar_evidencia`, `robot_telegram_web.py` → `_sacar_captura` |
| Prueba de conexión | Comprueba que el token sea válido sin mandarle un mensaje a nadie. | `prueba_conexion.py` |
| Lectura y validación de ticket | Gemini devuelve texto; se normalizan formatos conocidos y solo se muestran ingredientes válidos. | `procesador_factura.py`, `compras.py` → `interpretar_respuesta_factura` |
| Tiempo máximo Gemini | El lector completo tiene un límite de 60 segundos; al vencer, se limpian procesos TagUI y el bot ofrece carga manual. | `bot.py` → `ejecutar_lector_factura` |
| Confirmación de compra | El stock solo se actualiza cuando la persona confirma los totales proyectados. | `bot.py` → `atender_boton_de_factura`, `compras.py` → `sumar_al_stock` |
| Evidencia del ticket | Se guarda una copia local en `docs/evidencia/facturas/`, excluida de Git porque puede contener datos personales. | `bot.py` → `archivar_foto_factura` |
| Disponibilidad de receta | Compara ingredientes requeridos y stock; informa si alcanza o qué cantidades faltan. | `compras.py` → `faltantes_para_receta`, `bot.py` → `receta:disponibilidad` |

---

## 4. Implementación

```
Telegram (/start + botones)                          ← DISPARADOR
      │
      ▼
bot.py  ──►  compras.py  ──►  lee BaseDatos.csv, StockActual.csv, Menu.csv
      │           │              calcula: necesario − disponible = faltante
      │           ▼
      │      lista de compras
      ▼
robot_telegram_web.py (TagUI)                         ← PARTE RPA
  abre Chrome → Telegram Web → busca el grupo → pega → envía → captura
      │
      ▼
bot.py confirma con la captura   (si el robot falla: manda la lista por la Bot API)
```

  **Carga de factura (Etapa 2):** el bot descarga la foto, archiva una copia local y llama
  al lector TagUI de Gemini. `compras.py` normaliza y valida los renglones; el bot muestra
  los totales proyectados en el chat privado y espera Confirmar/Cancelar. Si la lectura
  falla o supera 60 segundos, ofrece actualizar la alacena manualmente. La foto nunca
  modifica el stock sin confirmación.

| Archivo | Rol |
|---|---|
| `Ejecutables/bot.py` | Escucha a Telegram, muestra los botones, coordina todo y responde. |
| `Ejecutables/compras.py` | Lee y escribe los CSV, valida los datos y calcula la lista. |
| `Ejecutables/procesador_factura.py` | Maneja Gemini en Chrome con TagUI, adjunta el ticket y devuelve su respuesta. |
| `Ejecutables/robot_telegram_web.py` | El robot RPA: maneja Chrome con TagUI. |
| `Ejecutables/configuracion.py` | Lee `config.txt` y centraliza URL, selectores, timeout y plantilla de Gemini. |
| `Ejecutables/prueba_conexion.py` | Prueba el token sin enviar nada. |

La explicación detallada de cada archivo, función por función, está en
[`explicaciones-archivos/`](explicaciones-archivos/).

---

## 5. Conceptos teóricos aplicados

Los tres están marcados en el código con comentarios en MAYÚSCULAS, en el lugar exacto
donde ocurren, para poder mostrarlos en la demo.

### 5.1 — Retroalimentación negativa (lazo cerrado)

**En la teoría:** el sistema **mide la salida** (o el estado actual), la compara con la
**referencia** y corrige su acción. En la retroalimentación negativa:
**señal de error = referencia − señal de retroalimentación**, y eso mantiene al sistema
estable. Un sistema así es de **lazo cerrado**. Uno de lazo abierto no usa información
de la salida.

**En nuestro sistema:**

| Elemento del lazo | Qué es en el bot |
|---|---|
| Referencia (valor deseado) | Lo que hace falta para las comidas elegidas, según las recetas (`BaseDatos.csv`) |
| Medición / retroalimentación | Lo que hay en la alacena (`StockActual.csv`) |
| Señal de error | **Lo que falta = necesario − disponible**. Es literalmente la resta que hace `calcular_lista` en `compras.py` |
| Actuador | El robot que manda la lista al grupo para que se compre |
| Cierre del lazo | Después de comprar, la persona actualiza la alacena con 🥫 Mi alacena, y el próximo cálculo parte de ese nuevo estado |

**Ejemplo:** para "Milanesas con puré" la receta pide 0.2 kg de pan rallado. La alacena
dice que hay 0.1 kg, así que el bot pide solo **0.1 kg**. Si la alacena tuviera 0.5 kg,
no lo pediría. Sin esta retroalimentación (lazo abierto), el bot pediría siempre todo lo
de la receta, sin importar lo que ya hay.

**Limitación honesta:** hoy la "medición" del stock la hace una persona a mano. La
mejora de la sección 7 automatiza justamente ese sensor.

### 5.2 — Perturbación exógena

**En la teoría:** una perturbación es una señal no deseada que entra al sistema y altera
su comportamiento, aunque la entrada de referencia no cambie. Es **exógena** si viene de
**afuera** del sistema, por factores que el sistema no controla. Es **endógena** si nace
**adentro**, por sus propios componentes.

**En nuestro sistema** (todas vienen de afuera del bot):

- **Una comida del menú que no tiene receta cargada**, porque alguien editó `Menu.csv` a
  mano. El sistema no se cae: calcula el resto y avisa
  `⚠ No tienen receta cargada en BaseDatos.csv (no se cuentan): ...`. En el menú
  semanal esa comida aparece marcada con `⚠ sin receta`.
- **Un error de formato en un CSV** (por ejemplo, una cantidad escrita con letras). El
  bot lo informa con el archivo y la fila exactos.
- **Cambios en el entorno**: que Telegram cambie el diseño de su web, que se corte
  internet o que alguien bloquee la PC.

**Cómo el sistema rechaza estas perturbaciones:** valida los datos antes de usarlos,
avisa en vez de fallar en silencio y sigue funcionando con lo que sí está bien.

**Para contrastar:** una perturbación **endógena** sería que el propio TagUI o su Chrome
se cuelguen. Es un fallo de un componente interno, y el sistema también lo maneja: corta
el robot a los 3 minutos.

**Para mostrarlo en la demo:** cambiar a mano en `Menu.csv` un día por una comida que no
exista (por ejemplo `Domingo,Guiso de mondongo`) y pedir el menú de la semana.

### 5.3 — Error en estado estable

**En la teoría:** el error es la desviación entre la **salida deseada** y la **salida
real**. La respuesta de un sistema tiene una parte **transitoria**, que aparece apenas
llega la entrada y después desaparece, y un **estado estable**, que es la salida final.
El **error en estado estable** es la diferencia que queda en esa salida final.

**En nuestro sistema:**

- **Salida deseada:** la lista de compras publicada en el grupo de Telegram.
- **Respuesta transitoria:** los pasos del robot mientras trabaja. Telegram Web tarda en
  cargar, a veces se redibuja y pierde lo tipeado, y por eso el robot espera y
  reintenta. Esas oscilaciones se estabilizan solas.
- **Error en estado estable:** el cálculo salió bien, pero al terminar **la lista no
  llegó al grupo**: no hay sesión en Telegram Web, no encuentra el grupo, la PC está
  bloqueada o se cortó la conexión. La salida final queda distinta de la deseada.

**Cómo el sistema lo corrige:** en vez de quedarse con ese error, el bot **manda la
lista él mismo por la Bot API** junto con el motivo. La lista llega igual y la salida
final vuelve a ser la deseada. Está en `bot.py`, en `cerrar_menu_y_procesar`.

**Otro ejemplo, más chico:** los redondeos. Lo que se cuenta por `unidad` se redondea
para arriba (si hace falta media lechuga, se pide 1), y kg/lt se redondean a 2
decimales. Es una diferencia pequeña y **permanente** entre lo que exactamente se
necesita y lo que se pide, aceptada a propósito porque no se puede comprar media
lechuga.

---

## 6. Cronología, contratiempos y riesgos

### Cronología

1. **Agosto (20/08):** clase de introducción a RPA y TagUI. Elegimos TagUI.
2. **Primer intento: WhatsApp Web.** Un script de TagUI buscaba el contacto y escribía el
   mensaje. **Funcionaba**, pero lo abandonamos por el riesgo de que Meta bloquee el
   número por comportamiento de bot, y porque depender del diseño de WhatsApp Web era
   frágil. La evidencia quedó en [`evidencia/`](evidencia/).
3. **Versión 1 (principios de septiembre):** un script de TagUI puro, con menú por
   consola, lectura de los CSV y envío por la Bot API de Telegram.
4. **10/09: cambio de requisito.** Los docentes aclararon que Telegram solo vale como
   disparador de un proceso local que actúe como un usuario.
5. **Versión 2 (la que se entrega):** pasamos a Python con la librería `rpa`. El bot de
   Telegram con botones es el disparador, y el robot maneja Chrome y escribe en Telegram
   Web.
6. **Fines de septiembre:** agregamos ver y cargar recetas, editar y sortear el menú y
   mantener la alacena desde el bot. Terminamos la documentación.

### Contratiempos y cómo se resolvieron

| Contratiempo | Solución |
|---|---|
| En la v1, el paso `run` de TagUI **crasheaba PhantomJS** en Windows al llamar a `curl` (es un bug conocido de TagUI). | Se reemplazó por el paso `api`, que hace la llamada HTTP directamente. |
| El paso `api` **fallaba en silencio** cuando la URL estaba en una variable. | Leyendo el código de TagUI encontramos que busca el texto literal `api http` para habilitar la llamada. Lo agregamos en un comentario, que es el mismo truco que usa TagUI internamente. |
| Creíamos que TagUI leía planillas sin Excel, pero su comando `excel` **requiere Excel instalado**. | Usamos CSV leídos como texto plano, que funcionan en cualquier sistema. |
| La primera vez, **Chrome se abría y no pasaba nada**. | Al estrenar el perfil, Chrome le cierra a TagUI la pestaña que iba a manejar. Se resuelve cortando y volviendo a correr, y quedó en el instructivo. |
| El buscador de Telegram **mezcla tus chats con canales públicos de desconocidos** que tienen el mismo nombre. | El robot solo acepta resultados de tus chats y nunca de la búsqueda global. Lo corregimos **antes** del primer envío. |
| **Con la PC bloqueada**, Telegram Web queda en blanco y el robot se colgaba. | Tiempo máximo de 3 minutos, más el plan B por la Bot API. |
| TagUI convierte cada salto de línea en Enter, así que **la lista iba a salir en 14 mensajes** separados. | La lista se **pega** entera (como Ctrl+V) y después se toca "enviar". |
| La captura mostraba **la lista de chats de la persona**. | Se recorta a la columna del chat abierto. |

### Riesgos y desafíos (análisis de impacto)

- **Cambios en Telegram Web:** es el riesgo más probable, porque es propio de todo RPA
  que opera sobre una interfaz. Lo mitigan los selectores centralizados y el plan B.
- **Necesita la sesión de la PC abierta:** es una limitación de todo RPA que maneja la
  pantalla. El bot no puede atender con la PC bloqueada.
- **Seguridad:** el bot pone a trabajar un robot en la PC de alguien. Por eso solo
  atiende a un chat, el token no se sube al repositorio y el robot no escribe fuera de
  los chats propios.
- **Calidad de los datos:** si la alacena o las recetas están mal, la lista sale mal. Lo
  mitigan las validaciones y los avisos.
- **Linux:** el código no tiene nada exclusivo de Windows, pero la instalación en Linux
  **todavía no se probó**. Es el desafío principal para la Etapa 2.

---

## 7. Mejora implementada en la Etapa 2: cargar la factura con una foto

### Flujo implementado

1. La persona toca **🧾 Cargar factura** en el chat privado del bot y envía la foto.
2. `bot.py` descarga el archivo desde Telegram y guarda una copia local en
   `docs/evidencia/facturas/`. Esa carpeta está excluida de Git para no publicar tickets
   que pueden contener datos personales.
3. `procesador_factura.py` inicia TagUI, abre Gemini en el Chrome de TagUI, adjunta el
   archivo y pide una respuesta plana, un producto por renglón.
4. `configuracion.py` centraliza la URL, los selectores, el timeout y la plantilla del
   prompt. El prompt recibe los nombres y unidades conocidos de recetas/alacena para
   reducir variantes como "PAPA" frente a "Papa"; la respuesta no debe repetir esa lista.
5. `compras.py` normaliza respuestas con nombre primero o cantidad primero, acepta
   decimales con coma, valida nombres/unidades y calcula el stock proyectado. Las líneas
   narrativas o incompatibles no se muestran como ingredientes.
6. El bot muestra en el **chat privado** solo los productos leídos y el total proyectado.
   La persona elige **✅ Confirmar** o **❌ Cancelar**. El stock solo se modifica al
   confirmar; después se muestra la alacena completa y el botón **🏠 Volver al menú**.
7. Si el lector falla o supera el límite de **60 segundos**, el bot ofrece **🥫 Cargar
   manualmente** o volver al menú. La lista de compras calculada desde recetas continúa
   enviándose al grupo configurado mediante Telegram Web.

### Controles y límites

- La foto se envía a un servicio externo (Gemini). No se deben enviar datos personales
  que no sean necesarios. La evidencia local debe borrarse cuando ya no haga falta.
- La confirmación humana es obligatoria porque la IA puede omitir o interpretar mal un
  producto. Solo se suman las líneas que superaron la validación.
- Los productos conocidos deben mantener la misma unidad que tienen en las recetas y
  el stock. El bot no inventa conversiones de peso/volumen; las cantidades contables
  explícitas, como una docena, se expresan como unidades.
- La navegación por Gemini depende de selectores web centralizados en
  `Ejecutables/configuracion.py`; si su interfaz cambia, esos selectores pueden requerir
  actualización.
- El archivo de configuración admite overrides opcionales `FACTURA_*`; los valores
  predeterminados y la plantilla están en `configuracion.py`.
