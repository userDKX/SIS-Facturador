# Ejemplos

Carpeta con payloads y scripts listos para usar contra el API.

## Payloads JSON

| Archivo                          | Para qué                                                             |
|----------------------------------|----------------------------------------------------------------------|
| `factura.json`                   | Factura tipo `01` con dos líneas, receptor RUC                       |
| `boleta.json`                    | Boleta tipo `03` con receptor DNI                                    |
| `boleta_consumidor_final.json`   | Boleta a "consumidor final" (`schemeID=0`, sin doc — solo boletas)   |
| `nota_credito_factura.json`      | Nota de crédito tipo `07` motivo `01` (anulación) contra una factura |
| `nota_credito_boleta.json`       | Nota de crédito tipo `07` motivo `06` (devolución total) contra una boleta |

## Scripts y snippets

| Archivo            | Para qué                                                                         |
|--------------------|----------------------------------------------------------------------------------|
| `curl_examples.sh` | Bash con curl. Por defecto apunta a `http://localhost:8000`; setea `BASE_URL` para apuntar al deploy. |
| `request.http`     | Snippets para la extensión REST Client de VS Code o IntelliJ HTTP Client.        |
| `expected_cdr.xml` | Ejemplo del CDR que SUNAT devuelve cuando acepta el comprobante (anonimizado).   |

## Cómo usarlos

Con el server corriendo (`make run`):

```bash
# Bash
bash examples/curl_examples.sh

# o un curl manual
curl -X POST http://localhost:8000/v1/invoices \
  -H "Content-Type: application/json" \
  -d @examples/boleta.json
```

Si vas a usarlo contra el deploy de Vercel:

```bash
BASE_URL="https://tu-deploy.vercel.app" bash examples/curl_examples.sh
```

## Sobre los datos de ejemplo

Los RUC, DNI y razones sociales son **ficticios** (el RUC `20512345678` no
existe, el DNI `12345678` es genérico). Si los usas tal cual contra
producción, SUNAT te va a devolver `2017 - El RUC no existe` o similar.
Reemplazalos con datos reales antes de emitir en `prod`.

Para pruebas en `beta` con MODDATOS, esos datos sí funcionan — `beta`
acepta cualquier RUC/DNI sintético porque no valida contra el padrón real.
