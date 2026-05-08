# Instalación

Esta guía te lleva de una máquina limpia a un API corriendo localmente que
puede firmar y enviar una Factura a SUNAT en su entorno de pruebas (`beta`).
**No** cubre envíos a producción real — para eso, después de instalar,
léete [`SUNAT_SETUP.md`](./SUNAT_SETUP.md).

## Lo que necesitas tener

| Herramienta | Mínimo  | Para qué                                            |
|-------------|---------|-----------------------------------------------------|
| Python      | 3.11    | FastAPI 0.115 + Pydantic 2 + SQLAlchemy 2.0         |
| Git         | 2.40    | Para clonar y contribuir                            |
| Postgres    | 14+     | Local instalado o un proyecto Supabase free         |
| Editor      | —       | VS Code es lo más común                             |

En Windows, `signxml` y `psycopg` a veces piden las **Visual C++ Build Tools**
("Desktop development with C++") porque pip no encuentra wheel compilado. Si
pip te tira `Microsoft Visual C++ 14.0 or greater is required`, instala las
build tools desde el Visual Studio Installer y reintenta.

En macOS, a veces necesitas `brew install libpq` para que `psycopg` enlace.

## 1. Clonar y crear el venv

PowerShell (Windows):

```powershell
git clone https://github.com/userDKX/SIS-Facturador.git
cd SIS-Facturador
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

bash / zsh (macOS, Linux, WSL):

```bash
git clone https://github.com/userDKX/SIS-Facturador.git
cd SIS-Facturador
python -m venv .venv
source .venv/bin/activate
```

Tip si tienes el `C:` casi lleno en Windows: el `.venv/` pesa harto. Crea el
venv en otro disco (`python -m venv D:\venvs\sis-facturador`) y ajusta la
ruta de activación.

## 2. Instalar dependencias

Para correrlo nomás:

```bash
pip install -r requirements.txt
```

Para correrlo y poder lintear / testear con cobertura:

```bash
pip install -e ".[dev]"
# equivalente:
pip install -r requirements-dev.txt
```

## 3. Configurar el `.env`

```powershell
Copy-Item .env.example .env    # Windows
```

```bash
cp .env.example .env           # Mac/Linux
```

Los defaults usan el **certificado público de pruebas MODDATOS** que SUNAT
publica para que cualquier dev pueda probar contra `beta` sin tener un cert
propio:

```env
MODE=beta
SUNAT_RUC=20000000001
SUNAT_USER=MODDATOS
SUNAT_PASSWORD=MODDATOS
CERT_PASSWORD=MODDATOS
# CERT_PFX_BASE64= <lo llenas en el siguiente paso>
DATABASE_URL=postgresql://postgres:password@localhost:5432/sis_facturador_dev
STORAGE_BACKEND=local
```

Te falta llenar `DATABASE_URL` (cualquier Postgres alcanzable) y
`CERT_PFX_BASE64` (paso siguiente).

## 4. Pasar el `.pfx` a base64

El cert vive en una env var como base64 para que pueda viajar al secret store
de Vercel sin tocar disco.

Para MODDATOS, baja el `.pfx` oficial desde la
[página de SUNAT con materiales de prueba](https://cpe.sunat.gob.pe/node/88)
(buscas el etiquetado "Certificado de prueba para los emisores
electrónicos") y conviértelo:

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("MODDATOS.pfx")) | Set-Clipboard
# y pegas en .env como CERT_PFX_BASE64=<paste>
```

bash:

```bash
base64 -w0 MODDATOS.pfx | pbcopy                          # macOS
base64 -w0 MODDATOS.pfx | xclip -selection clipboard      # Linux
```

Cross-platform con Python:

```bash
python -c "import base64; print(base64.b64encode(open('MODDATOS.pfx','rb').read()).decode())"
```

## 5. Validar el cert localmente (sin tocar SUNAT)

```bash
make verify-cert
# o
python scripts/verify_cert.py
```

Debe terminar con `OK - firma verificada`. Si te sale
`cryptography: invalid PKCS12 password` es porque tu `CERT_PASSWORD` está
mal.

## 6. Primer envío real (a beta)

```bash
make sendbill-beta
# o
python scripts/sendbill_beta.py
```

Esto manda una Factura sintética a `https://e-beta.sunat.gob.pe`. Si todo
salió bien, te imprime `Status accepted` y `code=0` del CDR. El XML firmado
y el CDR quedan guardados en `storage/test/beta/`.

## 7. Levantar el API

```bash
make run
# o
uvicorn app.main:app --reload
```

Y abres:

- `http://localhost:8000/v1/health` — healthcheck
- `http://localhost:8000/v1/health/cert` — metadata del cert (subject,
  vigencia, RUC)
- `http://localhost:8000/docs` — Swagger UI

## 8. Mandar tu primer comprobante por HTTP

Con el server corriendo, en otra terminal:

```bash
curl -X POST http://localhost:8000/v1/invoices \
  -H "Content-Type: application/json" \
  -d @examples/factura.json
```

Lista de payloads listos para usar en `examples/` (factura, boleta,
boleta a consumidor final).

## 9. Ir a producción

Cuando quieras mandar comprobantes reales contra `https://e-factura.sunat.gob.pe`,
**párate aquí** y léete [`SUNAT_SETUP.md`](./SUNAT_SETUP.md). Producción
tiene prerequisitos del lado de SUNAT (registrar el cert real, tener un
secundario con los permisos correctos, esperar las 24 horas de propagación)
que no son negociables.

## Cosas que pueden fallar instalando

| Síntoma                                                          | Probable causa / fix                                                                |
|------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| `pip install signxml` revienta con error de build de `lxml` (Win) | Instala Visual C++ Build Tools, después `pip install --upgrade pip` y reintenta     |
| `psycopg.errors.OperationalError` al correr tests                | Tu `DATABASE_URL` apunta a una BD que no existe; créala o usa Supabase              |
| `cryptography: invalid PKCS12 password`                          | El `CERT_PASSWORD` no coincide. Para MODDATOS es `MODDATOS`                         |
| `WSDL local no encontrado`                                       | Asegúrate de que clonaste el repo completo (los WSDL están en `app/sunat/wsdl/`)    |
| `0102 - Usuario o contraseña inválidos` desde beta               | `SUNAT_USER` debe ser `MODDATOS` (sin el RUC adelante — el código lo concatena)     |
| `0111` desde prod                                                | Espera 24h calendario después de Grabar permisos del secundario en SOL              |
| Tests skip con "CERT_PFX_BASE64 / CERT_PASSWORD no configurados" | Es esperado para los tests que dependen del cert; configura tu `.env` si los quieres correr |
