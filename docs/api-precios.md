# API de precios, tasas y fuentes regulatorias

Esta API sirve los precios que el scraper guarda en PostgreSQL. Otro proyecto los lee por HTTP. No hace falta estar en la misma red de Docker ni conocer la base.

La data vive **3 días**: cada fila con `fecha_dato` anterior a ese plazo se borra. El scrape corre todos los días a las **00:00 America/Santo_Domingo**. farmacias.do no se scrapea y no aparece en ninguna respuesta.

## Base

```
http://104.248.56.16:8099
```

El mismo servicio también responde en el puerto 80, que es la entrada compartida del servidor:

```
http://104.248.56.16
```

Solo hay métodos `GET`. La respuesta es JSON (`Content-Type: application/json`). No hay cuerpo en las peticiones.

Clave de esta instalación (`API_KEY` en `/var/www/altocosto-medicamentos/.env`):

```
cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU
```

## Autenticación

`/api/v1/salud` es público. Todos los demás endpoints `/api/v1/` exigen la misma clave, incluidos `/tasas`, `/fda`, `/purple-book` y `/ema`. Basta uno de estos headers:

```
X-API-Key: cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU
```

```
Authorization: Bearer cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU
```

Si faltan los dos, o el valor no coincide, la respuesta es `401`:

```json
{ "ok": false, "error": "API key inválida" }
```

## Uso desde otro proyecto

Python:

```python
import os
import requests

BASE = os.environ.get("ALTOCOSTO_API_BASE", "http://104.248.56.16:8099")
API_KEY = os.environ["ALTOCOSTO_API_KEY"]
headers = {"Authorization": f"Bearer {API_KEY}"}

fuentes = requests.get(f"{BASE}/api/v1/fuentes", headers=headers, timeout=60)
fuentes.raise_for_status()

offset = 0
limite = 2000
filas = []
while True:
    pagina = requests.get(
        f"{BASE}/api/v1/precios",
        headers=headers,
        params={"limite": limite, "offset": offset},
        timeout=120,
    )
    pagina.raise_for_status()
    cuerpo = pagina.json()
    if not cuerpo.get("ok"):
        raise RuntimeError(cuerpo.get("error") or cuerpo)
    lote = cuerpo.get("filas") or []
    filas.extend(lote)
    offset += limite
    if not lote or offset >= int(cuerpo.get("total") or 0):
        break
```

El mismo cliente con el otro header cambia solo el diccionario:

```python
headers = {"X-API-Key": API_KEY}
```

Variables para el otro proyecto:

```
ALTOCOSTO_API_BASE=http://104.248.56.16:8099
ALTOCOSTO_API_KEY=cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU
```

## Endpoints

### Salud del servicio

Comprueba que el proceso responde y que la base está conectada. No pide clave.

```
GET /api/v1/salud
```

`200` si la base responde. `503` si no.

```json
{
  "ok": true,
  "mensaje": "Conectado a PostgreSQL",
  "retencion_dias": 3,
  "database": "altocosto",
  "schema_ok": true
}
```

`ok` es el campo que importa. El resto describe la conexión.

### Resumen por farmacia

Lista cada farmacia que tiene filas guardadas, con el conteo y la fecha más reciente. Sirve para saber qué hay antes de bajar el detalle.

```
GET /api/v1/fuentes
```

Pide clave. `200` si sale bien.

```json
{
  "ok": true,
  "total": 2785,
  "retencion_dias": 3,
  "fuentes": [
    {
      "pais": "Brasil",
      "farmacia": "Pague Menos",
      "filas": 184,
      "fecha": "2026-09-25"
    }
  ]
}
```

| Campo | Significado |
| --- | --- |
| `total` | Filas de precios en total, ya sin farmacias.do |
| `retencion_dias` | Días que una fila permanece en este servidor |
| `fuentes[].pais` | País de la farmacia |
| `fuentes[].farmacia` | Nombre con el que se guardó la fuente |
| `fuentes[].filas` | Cuántos precios hay de esa farmacia |
| `fuentes[].fecha` | `fecha_dato` más nueva de esa farmacia (`AAAA-MM-DD`) |

### Precios

Devuelve las filas de `medicamentos_altos_costos_america`. Es el endpoint para llevarse la data.

```
GET /api/v1/precios
```

Pide clave. `200` si sale bien. `500` si la consulta falla; el cuerpo trae `ok: false` y `error`.

Ejemplo para bajar la primera página completa:

```bash
curl -sS -H "Authorization: Bearer cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU" \
  "http://104.248.56.16:8099/api/v1/precios?limite=2000&offset=0"
```

Equivalente con API key:

```bash
curl -sS -H "X-API-Key: cwXheLmixbn6B_Vmb_7m4uvPqDjHvVx6XJisK5lV0bU" \
  "http://104.248.56.16:8099/api/v1/fuentes"
```

#### Parámetros

Todos son opcionales y van en la query string.

| Parámetro | Qué hace |
| --- | --- |
| `limite` | Filas de esta página. Por defecto `500`. Máximo `2000`. Si pides más, se recorta a 2000. |
| `offset` | Cuántas filas saltar. Por defecto `0`. Para la página siguiente suma el `limite`. |
| `pais` | Igualdad exacta. Ejemplo: `Brasil`, `República Dominicana`. |
| `farmacia` | Igualdad exacta, el mismo texto que devuelve `/api/v1/fuentes`. Ejemplo: `Pague Menos`. |
| `q` | Texto contenido en el nombre de la lista, el nombre comercial o el principio activo. No distingue mayúsculas. |
| `n_lista` | Número del medicamento en la lista DAMAC/FOMAC. |
| `fecha` o `fecha_dato` | Solo ese día, formato `AAAA-MM-DD`. |

Varios filtros se combinan con AND. Un ejemplo de una farmacia y un medicamento:

```
GET /api/v1/precios?pais=Chile&farmacia=Salcobrand&q=adalimumab&limite=2000&offset=0
```

#### Cómo bajar todo

Una llamada no trae más de 2000 filas. El campo `total` es el conteo con los filtros aplicados, no el tamaño de `filas`.

1. Llama con `limite=2000` y `offset=0`.
2. Guarda `filas`.
3. Si `offset + limite` es menor que `total`, vuelve a llamar sumando 2000 al `offset`.
4. Para cuando `filas` venga vacío o el offset alcance `total`.

```
offset=0
offset=2000
offset=4000
```

El orden es estable: `fecha_dato` descendente, luego `n_lista`, `pais`, `farmacia` e `id`.

#### Cuerpo de la respuesta

```json
{
  "ok": true,
  "total": 2785,
  "limite": 2000,
  "offset": 0,
  "retencion_dias": 3,
  "filas": [
    {
      "id": 1,
      "pais": "República Dominicana",
      "farmacia": "FarmaValue",
      "fuente_url": "https://www.farmavalue.com/do/products/123-ejemplo",
      "id_producto_farmacia": "123",
      "sku": null,
      "n_lista": 5,
      "medicamento_lista": "Adalimumab",
      "programa": "DAMAC",
      "nombre_comercial": "Humira",
      "principio_activo": "Adalimumab",
      "concentracion": "40 mg",
      "presentacion": "jeringa",
      "laboratorio": null,
      "precio": 15000.0,
      "precio_lista": 16000.0,
      "precio_oferta": 15000.0,
      "moneda": "DOP",
      "disponibilidad": "disponible",
      "calidad": "ok",
      "observacion": null,
      "fecha_dato": "2026-09-25",
      "fecha_registro": "2026-09-25",
      "fecha_actualizacion": "2026-09-25T04:10:00"
    }
  ]
}
```

| Campo de cada fila | Significado |
| --- | --- |
| `id` | Identificador interno. Cambia si la fila se vuelve a crear. |
| `pais` | País de la oferta. |
| `farmacia` | Farmacia o fuente de precio. |
| `fuente_url` | Página del producto en la farmacia, cuando el scraper la tiene. |
| `id_producto_farmacia` | Id del producto en esa farmacia. |
| `sku` | SKU, si la fuente lo trae. |
| `n_lista` | Número en la lista de medicamentos de alto costo. |
| `medicamento_lista` | Nombre del principio en esa lista. |
| `programa` | Programa de la lista, por ejemplo DAMAC o FOMAC. |
| `nombre_comercial` | Marca o nombre en la farmacia. |
| `principio_activo` | Principio activo leído de la ficha. |
| `concentracion` | Concentración, cuando se pudo leer. |
| `presentacion` | Presentación (caja, jeringa, etc.). |
| `laboratorio` | Laboratorio, si viene en la ficha. |
| `precio` | Precio usado para comparar, en la moneda de la fila. |
| `precio_lista` | Precio de lista, si la fuente distingue lista y oferta. |
| `precio_oferta` | Precio de oferta, si es menor que el de lista. |
| `moneda` | Código de 3 letras (`DOP`, `BRL`, `MXN`, `USD`, …). |
| `disponibilidad` | Texto de stock que dejó el scraper. |
| `calidad` | Qué tan seguro es el cruce con la lista (`ok` u otro valor de revisión). |
| `observacion` | Nota del scraper. Vacío si no hubo aviso. |
| `fecha_dato` | Día del dato. Es la fecha que usa la retención de 3 días. |
| `fecha_registro` | Día en que se insertó la fila. |
| `fecha_actualizacion` | Última vez que se actualizó. |

Los precios van en la moneda de la farmacia. Esta API no los convierte a dólares.

## Qué no incluye

- No hay alta, baja ni modificación de precios por esta API.
- No devuelve filas de farmacias.do ni URLs de ese dominio.
- No incluye el historial de tendencias de precios. FDA, Purple Book y EMA se exponen en los endpoints descritos abajo.
- Los precios se purgan a los 3 días. Las nuevas exportaciones conservan el último snapshot completo de cada fuente hasta que se publica su reemplazo.


## Tasas y fuentes regulatorias (sincronización diaria)

El mismo flujo diario de las **00:00 America/Santo_Domingo**, después de las farmacias principales, actualiza tasas, Purple Book, EMA y FDA, en ese orden. FDA reutiliza Purple Book y refresca Orange Book y Purple Book Patent List antes de consultar openFDA/Drugs@FDA/DailyMed para cada principio DAMAC/FOMAC. Cada paso queda registrado en el log de la corrida. No se inicia ninguna descarga externa al leer la API.

Los snapshots se publican de forma atómica por fuente en `cache/api_v1/`, volumen compartido por cron y API. Ante un fallo se mantiene el último snapshot completo de esa fuente y se registra el error. Una corrida puede terminar a distinta hora según las fuentes externas; el consumidor debe revisar las fechas y los estados, no asumir que a las 00:00 ya están listas.

### Nuevos endpoints

Todos son `GET`, usan la misma API key y devuelven `filas` paginadas (`limite=500`, máximo `2000`, `offset=0`).

| Endpoint | Contenido y enlaces de origen |
| --- | --- |
| `/api/v1/tasas` | Unidades de moneda local por **1 USD**, moneda, país, tasa, fecha del dato y fuente efectiva. |
| `/api/v1/fda` | Información por principio: indicaciones, biológico/genérico/biosimilar/intercambiable, aprobaciones tentativas, productos FDA, patentes, exclusividades y enlaces de etiquetas/PDF cuando están disponibles. |
| `/api/v1/purple-book` | Productos biológicos cruzados con DAMAC/FOMAC: BLA, solicitante, marca, licencia, biosimilar/intercambiable, presentación, aprobación, exclusividades y URL del CSV de origen. |
| `/api/v1/ema` | Medicamentos humanos cruzados con DAMAC/FOMAC: número EMA, estado, INN, sustancia activa, indicaciones, titular, fechas de autorización, flags de genérico/biosimilar/huérfano y enlace EPAR (`medicine_url`). |

### Fuentes en `/api/v1/fuentes`

Se conserva `fuentes` con el resumen de farmacias y `total` con el conteo de precios. Se agregan:

| Campo | Contenido |
| --- | --- |
| `monedas` | Catálogo de monedas, países, banco si aplica, portal (`link`), URL de datos (`fuente_datos_url`) y reserva (`reserva_url`). |
| `regulatorias` | Catálogo de fuentes FDA, Drugs@FDA, Orange Book, Purple Book, Patent List y EMA, con enlaces y endpoint de exportación. |
| `exportaciones` | Objeto con claves `tasas`, `fda`, `purple-book`, `ema`; cada una informa endpoint, disponibilidad, total, fecha de publicación, desactualización y estado de la última ejecución. |

### Tasas por país

| Moneda / país | Fuente principal existente |
| --- | --- |
| DOP / República Dominicana | BCRD, venta; incluye `compra` cuando se obtuvo del banco. |
| ARS / Argentina | Dólar oficial venta BCRA vía dolarapi.com. |
| BRL / Brasil | Banco Central do Brasil, PTAX venta. |
| COP / Colombia | TRM, Banco de la República / Superintendencia Financiera vía datos.gov.co. |
| PEN / Perú | BCRP, serie PD04646PD, cierre venta. |
| CLP / Chile | Dólar observado BCCh vía mindicador.cl. |
| MXN / México | Banxico FIX, SF43718. |
| PAB / Panamá | Paridad fija 1:1 con USD. |
| CRC, HNL, GTQ, NIO, UYU, PYG, GYD, TTD, BOB, VES, CAD | Reserva de mercado open.er-api.com, utilizada por las fuentes existentes. |

Si falla la fuente principal bancaria se usa la reserva, con `es_reserva: true`, `fuente: "open.er-api.com"` y su URL efectiva. No se presenta la reserva como dato oficial del banco. `fecha` es la fecha que informa la fuente (puede ser un periodo textual para BCRP o vacía si la fuente no la aporta); `actualizado_en` es la fecha y hora en que este servidor publicó el snapshot, con zona horaria. Los días sin cotización puede conservarse la fecha del último día hábil. USD es la moneda base y no necesita una tasa propia.

Ejemplo de estructura (valores ilustrativos):

```json
{
  "ok": true,
  "fuente": "tasas",
  "total": 19,
  "limite": 500,
  "offset": 0,
  "actualizado_en": "2026-10-12T09:00:00-04:00",
  "desactualizado": false,
  "actualizacion": {
    "estado": "ok",
    "inicio": "2026-10-12T08:59:00-04:00",
    "fin": "2026-10-12T09:00:00-04:00"
  },
  "filas": [
    {
      "moneda": "DOP",
      "pais": "República Dominicana",
      "moneda_base": "USD",
      "valor": 61.8247,
      "compra": 61.1168,
      "nombre": "BCRD venta",
      "fecha": "2026-10-09",
      "fuente": "Banco Central de la República Dominicana",
      "link": "https://www.bancentral.gov.do/",
      "fuente_datos_url": "https://www.bancentral.gov.do/",
      "es_reserva": false
    }
  ]
}
```

### Filtros y campos regulatorios

Los nuevos endpoints aceptan `limite`, `offset`, `n_lista`, `q`, `pais`, `moneda` y `fecha`/`fecha_dato`. Solo aplica un filtro si el campo existe en las filas del recurso: por ejemplo, `moneda` en tasas y `n_lista` en regulatorios; filtrar un campo inexistente devuelve cero filas. `q` busca en nombres de medicamento, marca, INN y sustancia activa sin distinguir mayúsculas. Se pueden descargar todos los principios sin indicar `n_lista`.

```text
GET /api/v1/tasas?moneda=DOP
GET /api/v1/fda?n_lista=5
GET /api/v1/purple-book?n_lista=5&limite=2000
GET /api/v1/ema?q=adalimumab&limite=2000
```

En FDA las colecciones `tentative`, `patentes`, `exclusividades`, `productos_fda` y `fuentes` son arrays JSON, no cadenas JSON. Se conservan los campos de los lectores regulatorios existentes. Puede haber campos vacíos si la fuente no informa el dato o no se encuentra un cruce; eso no demuestra ausencia de aprobación, patentes o indicaciones.

`fecha_dato` en FDA y EMA identifica el día del snapshot diario. En Purple Book identifica el periodo mensual del CSV publicado por FDA; `periodo_etiqueta` conserva ese periodo. Una revisión diaria no implica que FDA publique un CSV nuevo cada día. `actualizado_en` permite saber cuándo se volvió a descargar y procesar.

### Estado, errores y consumo diario

`actualizacion.estado` puede ser `pendiente`, `running`, `ok` o `error`. Incluye `inicio`, `fin` y `error` cuando corresponde. `desactualizado` indica que el snapshot disponible se publicó antes del día actual en America/Santo_Domingo; no afirma que el banco o regulador haya publicado un dato nuevo.

- `200`: último snapshot completo disponible, incluso si una actualización posterior sigue en ejecución o falló. Revisa `actualizado_en`, `desactualizado` y `actualizacion`.
- `401`: API key inválida o ausente.
- `503`: aún no existe ningún snapshot completo de esa fuente; `ok: false`, `filas: []` y detalle del estado. Reintenta después; no borres los datos del consumidor.
- `500`: error de lectura o procesamiento de la petición.

Para sincronizar, descarga todas las páginas de cada recurso y reemplaza su copia local **solo cuando la descarga completa haya terminado**. Guarda `actualizado_en`; si cambia entre páginas, reinicia la descarga del recurso para evitar mezclar snapshots. Si no cambia desde la sincronización anterior, puedes omitir la descarga. Conserva por separado la fecha del dato original. Este mismo patrón permite detectar que un snapshot ha quedado antiguo y reintentar cuando el cron termine.

```python
import os
import requests

base = os.environ["ALTOCOSTO_API_BASE"].rstrip("/")
headers = {"Authorization": f"Bearer {os.environ['ALTOCOSTO_API_KEY']}"}

for recurso in ("tasas", "fda", "purple-book", "ema"):
    filas = []
    offset = 0
    version = None
    while True:
        r = requests.get(
            f"{base}/api/v1/{recurso}", headers=headers,
            params={"limite": 2000, "offset": offset}, timeout=120,
        )
        r.raise_for_status()  # 503/error: conservar copia local y reintentar luego
        data = r.json()
        if not data["ok"]:
            raise RuntimeError(data)
        if version is not None and version != data["actualizado_en"]:
            raise RuntimeError("Snapshot cambió; reiniciar descarga del recurso")
        version = data["actualizado_en"]
        filas.extend(data["filas"])
        offset += data["limite"]
        if offset >= data["total"]:
            break
    # Reemplazar aquí la copia local del recurso en una transacción.
    print(recurso, len(filas), version)
```

Para reintentar manualmente una actualización sin repetir todas las farmacias:

```bash
docker exec altocosto-cron python scrapper/exportaciones_diarias.py
# O una fuente: --fuente tasas | purple-book | ema | fda
```

FDA requiere primero un snapshot de Purple Book. El orden sin `--fuente` respeta esa dependencia. Los errores no eliminan los snapshots anteriores. Cada fuente tiene un bloqueo para impedir actualizaciones simultáneas; si está en curso, un segundo intento devuelve código de salida 1 y no altera el snapshot.
