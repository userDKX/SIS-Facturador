"""EMISION REAL: envia una guia de remision remitente (tipo 09) a SUNAT produccion.

ATENCION: la GR emitida queda registrada en SUNAT y tiene efecto legal
sobre el traslado de bienes. Solo puede anularse con un procedimiento
ante SUNAT. Verifica los datos antes de ejecutar.

Requiere flag --confirm-real para correr. Sin ese flag, aborta.

Uso:
    python scripts/sendbill_prod_despatch.py --confirm-real

A diferencia de facturas/boletas (SOAP a billService), las GR usan la Nueva
GRE REST en api-cpe.sunat.gob.pe. Necesitas las credenciales API GRE en .env:
    GRE_CLIENT_ID=...
    GRE_CLIENT_SECRET=...
Se obtienen en SUNAT SOL > Credenciales API SUNAT (distintas del usuario SOL).

El .env puede quedarse en MODE=beta como default seguro — este script fuerza
MODE=prod localmente.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Forzar UTF-8 en stdout para que las respuestas de SUNAT (que contienen tildes)
# no rompan en consolas Windows con cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LIMA_TZ = timezone(timedelta(hours=-5))

if "--confirm-real" not in sys.argv:
    print("=" * 70)
    print("ABORTADO - falta flag --confirm-real")
    print("=" * 70)
    print()
    print("Este script EMITE una guia de remision real a SUNAT produccion.")
    print("Para correrlo agrega el flag explicito:")
    print()
    print("  python scripts/sendbill_prod_despatch.py --confirm-real")
    print()
    print("Una GR aceptada en prod NO se puede borrar. Verifica los datos.")
    sys.exit(1)

os.environ["MODE"] = "prod"

from sis_facturador.config import get_settings

get_settings.cache_clear()

from sunat_py import (
    Conductor,
    DespatchAdviceInput,
    DireccionTraslado,
    GRLine,
    GreResult,
    Party,
    Vehiculo,
    build_despatchadvice_xml,
    get_gre_token,
    load_cert_from_base64,
    pack_invoice,
    send_gre,
    sign_invoice_xml,
)
from sis_facturador.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Datos del remitente (emisor) — RUC viene de SUNAT_RUC en .env
# ---------------------------------------------------------------------------
EMISOR_RAZON = "MI EMPRESA SAC"
EMISOR_DIRECCION = "AV. PRINCIPAL 123 LIMA"

# ---------------------------------------------------------------------------
# Datos del destinatario
# ---------------------------------------------------------------------------
DESTINATARIO_TIPO_DOC = "6"  # 6 = RUC, 1 = DNI
DESTINATARIO_NUMERO_DOC = "20000000001"
DESTINATARIO_NOMBRE = "CLIENTE EJEMPLO SAC"
DESTINATARIO_DIRECCION = "AV. CLIENTE 456 LIMA"

# ---------------------------------------------------------------------------
# Datos del traslado
# ---------------------------------------------------------------------------
SERIE = "T001"
NUMERO = 1

MOTIVO_TRASLADO = "04"          # Catalogo SUNAT 20. 04 = Traslado entre establecimientos
MOTIVO_DESCRIPCION = "TRASLADO ENTRE ESTABLECIMIENTOS"
MODALIDAD = "02"                # Catalogo SUNAT 18. 01 = publico, 02 = privado

PESO_BRUTO_TOTAL = Decimal("10.00")
PESO_BRUTO_UNIDAD = "KGM"
NUMERO_BULTOS = 1

# Punto de partida
PARTIDA_UBIGEO = "150101"                  # INEI 6 digitos
PARTIDA_DIRECCION = "AV. PRINCIPAL 123 LIMA"
PARTIDA_COD_LOCAL = "0000"                 # "0000" casa matriz; "0001"+ anexos

# Punto de llegada
LLEGADA_UBIGEO = "150101"
LLEGADA_DIRECCION = "AV. CLIENTE 456 LIMA"
LLEGADA_COD_LOCAL = "0000"

# Conductor (modalidad privada). DNI debe existir en RENIEC (SUNAT lo valida).
CONDUCTOR_TIPO_DOC = "1"
CONDUCTOR_NUM_DOC = "00000000"
CONDUCTOR_NOMBRES = "NOMBRE"
CONDUCTOR_APELLIDOS = "APELLIDO"
CONDUCTOR_LICENCIA = "Q00000000"           # licencia vigente del conductor

# Vehiculo. Placa formato peruano (sin espacios). Ej: "ABC123", "A1B234".
VEHICULO_PLACA = "ABC123"

LINEAS = [
    GRLine(
        codigo="BIEN01",
        descripcion="BIENES EN TRASLADO",
        unidad="NIU",
        cantidad=Decimal("1"),
    ),
]


def main() -> int:
    print("=" * 70)
    print("EMISION PROD GUIA DE REMISION (Nueva GRE REST)")
    print("=" * 70)

    if not settings.GRE_CLIENT_ID or not settings.GRE_CLIENT_SECRET:
        print("\nFaltan GRE_CLIENT_ID / GRE_CLIENT_SECRET en .env.")
        print("Genera las credenciales en SUNAT SOL > Credenciales API SUNAT")
        print("(son distintas del usuario SOL y del certificado).")
        return 2

    print(f"\nAPI GRE     : api-cpe.sunat.gob.pe")
    print(f"RUC emisor  : {settings.SUNAT_RUC}")
    print(f"Usuario SOL : {settings.sunat_username}")
    print("\n--- Guia de Remision a emitir ---")
    print(f"  Serie/numero  : {SERIE}-{NUMERO}")
    print(f"  Motivo        : {MOTIVO_TRASLADO} - {MOTIVO_DESCRIPCION}")
    print(f"  Modalidad     : {MODALIDAD} (02=privado)")
    print(f"  Peso bruto    : {PESO_BRUTO_TOTAL} {PESO_BRUTO_UNIDAD}")
    print(f"  Destinatario  : {DESTINATARIO_NUMERO_DOC} - {DESTINATARIO_NOMBRE}")
    print(f"  Partida       : [{PARTIDA_UBIGEO}] {PARTIDA_DIRECCION}")
    print(f"  Llegada       : [{LLEGADA_UBIGEO}] {LLEGADA_DIRECCION}")
    print(f"  Conductor DNI : {CONDUCTOR_NUM_DOC}")
    print(f"  Vehiculo      : {VEHICULO_PLACA}")

    print("\n[1/5] Cargando cert...")
    bundle = load_cert_from_base64(settings.CERT_PFX_BASE64, settings.CERT_PASSWORD)
    print(f"      OK  CN={bundle.common_name}")

    emisor = Party(
        tipo_doc="6",
        numero_doc=settings.SUNAT_RUC,
        razon_social=EMISOR_RAZON,
        direccion=EMISOR_DIRECCION,
        ubigeo="0000",
    )
    destinatario = Party(
        tipo_doc=DESTINATARIO_TIPO_DOC,
        numero_doc=DESTINATARIO_NUMERO_DOC,
        razon_social=DESTINATARIO_NOMBRE,
        direccion=DESTINATARIO_DIRECCION,
    )

    gr = DespatchAdviceInput(
        serie=SERIE,
        numero=NUMERO,
        # Fecha en TZ Lima — el reloj de SUNAT corre en UTC-5 y rechaza fechas
        # fuera de su rango si tu OS esta en otra zona (error 2329).
        fecha_emision=datetime.now(LIMA_TZ).date(),
        motivo_traslado=MOTIVO_TRASLADO,
        motivo_descripcion=MOTIVO_DESCRIPCION,
        modalidad=MODALIDAD,
        peso_bruto_total=PESO_BRUTO_TOTAL,
        peso_bruto_unidad=PESO_BRUTO_UNIDAD,
        emisor=emisor,
        destinatario=destinatario,
        partida=DireccionTraslado(
            ubigeo=PARTIDA_UBIGEO,
            direccion=PARTIDA_DIRECCION,
            cod_local=PARTIDA_COD_LOCAL,
        ),
        llegada=DireccionTraslado(
            ubigeo=LLEGADA_UBIGEO,
            direccion=LLEGADA_DIRECCION,
            cod_local=LLEGADA_COD_LOCAL,
        ),
        lines=LINEAS,
        numero_bultos=NUMERO_BULTOS,
        conductor=Conductor(
            tipo_doc=CONDUCTOR_TIPO_DOC,
            numero_doc=CONDUCTOR_NUM_DOC,
            nombres=CONDUCTOR_NOMBRES,
            apellidos=CONDUCTOR_APELLIDOS,
            licencia=CONDUCTOR_LICENCIA,
        ),
        vehiculo=Vehiculo(placa=VEHICULO_PLACA),
    )

    filename_base = f"{settings.SUNAT_RUC}-09-{SERIE}-{NUMERO}"
    out_dir = REPO_ROOT / "storage" / "prod"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n[2/5] Construyendo + firmando UBL DespatchAdvice...")
    unsigned = build_despatchadvice_xml(gr)
    signed = sign_invoice_xml(unsigned, bundle)
    (out_dir / f"{filename_base}.xml").write_bytes(signed)
    print(f"      Firmado: {len(signed)} bytes -> {filename_base}.xml")

    print("\n[3/5] Empaquetando ZIP...")
    zip_bytes = pack_invoice(signed, filename_base)
    (out_dir / f"{filename_base}.zip").write_bytes(zip_bytes)
    print(f"      ZIP: {len(zip_bytes)} bytes")

    print("\n[4/5] Obteniendo token OAuth2 (Nueva GRE)...")
    try:
        token = get_gre_token(
            client_id=settings.GRE_CLIENT_ID,
            client_secret=settings.GRE_CLIENT_SECRET,
            ruc=settings.SUNAT_RUC,
            username=settings.SUNAT_USER,
            password=settings.SUNAT_PASSWORD,
        )
        print("      Token OK")
    except Exception as e:
        print(f"      *** ERROR obteniendo token: {e}")
        return 3

    print("\n[5/5] Enviando GRE a SUNAT y esperando CDR...")
    try:
        result: GreResult = send_gre(
            token=token,
            ruc=settings.SUNAT_RUC,
            zip_bytes=zip_bytes,
            filename_base=filename_base,
        )
    except Exception as e:
        print(f"      *** ERROR enviando GRE: {e}")
        return 3

    print(f"      Status      : {result.status}")
    print(f"      Code        : {result.code}")
    print(f"      Description : {result.description}")

    if result.cdr_zip:
        cdr_path = out_dir / f"R-{filename_base}.zip"
        cdr_path.write_bytes(result.cdr_zip)
        print(f"      CDR guardado: {cdr_path.relative_to(REPO_ROOT)}")

    print("\nVeredicto:")
    if result.status == "accepted":
        print("      *** ACEPTADA POR SUNAT - GR registrada ***")
        return 0
    if result.status == "accepted_with_obs":
        print("      ACEPTADA con observaciones")
        return 0
    print(f"      RECHAZADA ({result.code}) - revisar codigo y mensaje")
    return 1


if __name__ == "__main__":
    sys.exit(main())
