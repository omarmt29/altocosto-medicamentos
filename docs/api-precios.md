# API de precios de farmacias

Esta API sirve los precios que el scraper guarda en este servidor. Otro servidor puede leerlos por HTTP. La data vive **3 días**: cada fila con `fecha_dato` anterior a ese plazo se borra.

farmacias.do no se scrapea y no aparece en ninguna respuesta.

## Base

```
http://137.184.201.116:8099
```

Solo hay métodos `GET`. La respuesta es JSON.

## Autenticación

`/api/v1/salud` es público. El resto exige la clave.

Mándala en uno de estos headers:

```
X-API-Key: wEcGA9K2ptxRHFCwpOkHX2Ir_2UsjrcE
```

```
Authorization: Bearer wEcGA9K2ptxRHFCwpOkHX2Ir_2UsjrcE
```

Si falta o no coincide, la respuesta es `401`:

```json
{ "ok": false, "error": "API key inválida" }
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
curl -s -H "X-API-Key: wEcGA9K2ptxRHFCwpOkHX2Ir_2UsjrcE" \
  "http://137.184.201.116:8099/api/v1/precios?limite=2000&offset=0"
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
- No incluye el historial de tendencias ni los catálogos FDA/EMA. Solo la tabla vigente de precios.
- Pasados 3 días desde `fecha_dato`, la fila ya no está.
