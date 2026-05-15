"""Refresca el bundle de XSDs (OASIS UBL 2.1 + extensiones SUNAT).

Tool de mantenedor. Lo corre quien va a commitear una actualizacion del
bundle al repo, NO el usuario final del SDK (la wheel PyPI ya viene
con los XSDs adentro).

Que descarga:

1. OASIS UBL 2.1 oficial (Invoice, CreditNote, DebitNote, DespatchAdvice
   + common). URLs estables, estandar congelado desde 2013. ~3 MB.

2. Extensiones SUNAT (Retention, Perception, SummaryDocuments,
   VoidedDocuments + UBLPE-SunatAggregateComponents). Empaquetadas en
   un ZIP unico que SUNAT publica en cpe.sunat.gob.pe. Estos XSDs son
   UBL 2.0 + extensiones peruanas (SUNAT nunca publico version 2.1 para
   retencion/percepcion/RA/RC). ~600 KB.

Layout final del bundle:

    schemas/
    +-- ubl-2.1/        OASIS UBL 2.1 (factura/boleta/NC/ND/GRE)
    |   +-- maindoc/
    |   `-- common/
    `-- sunat-1.0/      SUNAT UBL 2.0 + extensiones (RA/RC/RET/PER)
        +-- maindoc/    UBLPE-*-1.0.xsd
        `-- common/     UBL 2.0 common + UBLPE-SunatAggregate

Uso:
    python scripts/refresh_xsd_schemas.py

Despues:
    git diff packages/core/src/sunat_py/xsd/schemas/
    git add packages/core/src/sunat_py/xsd/schemas/
    git commit -m "chore(xsd): refresh bundle"
"""

from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = (
    REPO_ROOT / "packages" / "core" / "src" / "sunat_py" / "xsd" / "schemas"
)
OASIS_DEST = SCHEMAS_DIR / "ubl-2.1"
SUNAT_DEST = SCHEMAS_DIR / "sunat-1.0"

OASIS_BASE = "https://docs.oasis-open.org/ubl/os-UBL-2.1/xsd"
SUNAT_ZIP_URL = (
    "https://cpe.sunat.gob.pe/sites/default/files/inline-files/"
    "Archivos%20XSD%20%281%29.zip"
)

# (subdir_rel, filename) — el targetNamespace observado se reporta en
# la salida del script, no lo hardcodeamos para no adivinar valores
# que cambien entre erratums.
#
# Nota: los CodeList_*.xsd (CurrencyCode, LanguageCode, etc.) viven
# dentro del ZIP completo UBL-2.1.zip y no se distribuyen como archivos
# sueltos en docs.oasis-open.org/xsd/common/. No los bundleamos porque
# validan que "PEN" sea "PEN" — costo > beneficio. Greenter tampoco los
# usa. Si en algun momento los necesitamos, hay que bajar el ZIP.
OASIS_XSDS: list[tuple[str, str]] = [
    # maindoc/ — XSDs raiz que sunat_py.xsd.validator carga
    ("maindoc", "UBL-Invoice-2.1.xsd"),
    ("maindoc", "UBL-CreditNote-2.1.xsd"),
    ("maindoc", "UBL-DebitNote-2.1.xsd"),
    ("maindoc", "UBL-DespatchAdvice-2.1.xsd"),
    # common/ — importados transitivamente por los raiz
    ("common", "UBL-CommonAggregateComponents-2.1.xsd"),
    ("common", "UBL-CommonBasicComponents-2.1.xsd"),
    ("common", "UBL-CommonExtensionComponents-2.1.xsd"),
    ("common", "UBL-CommonSignatureComponents-2.1.xsd"),
    ("common", "UBL-CoreComponentParameters-2.1.xsd"),
    ("common", "UBL-ExtensionContentDataType-2.1.xsd"),
    ("common", "UBL-QualifiedDataTypes-2.1.xsd"),
    ("common", "UBL-SignatureAggregateComponents-2.1.xsd"),
    ("common", "UBL-SignatureBasicComponents-2.1.xsd"),
    ("common", "UBL-UnqualifiedDataTypes-2.1.xsd"),
    ("common", "UBL-XAdESv132-2.1.xsd"),
    ("common", "UBL-XAdESv141-2.1.xsd"),
    ("common", "UBL-xmldsig-core-schema-2.1.xsd"),
    ("common", "CCTS_CCT_SchemaModule-2.1.xsd"),
]


def _fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "sunat-py-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL hardcoded
        return resp.read()


_XS_SCHEMA_TAG = "{http://www.w3.org/2001/XMLSchema}schema"


def _verify(content: bytes) -> tuple[str | None, str]:
    """Retorna (error, target_namespace_observado).

    Verifica solo que el archivo descargado sea un `xs:schema` valido —
    es decir, que no sea HTML "404", JSON de error, o XML random. No
    adivina el targetNamespace: el namespace observado se reporta en la
    salida para que el mantenedor lo revise.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return f"XML mal formado: {e}", ""
    if root.tag != _XS_SCHEMA_TAG:
        return f"root tag {root.tag!r} no es xs:schema", ""
    tns = root.get("targetNamespace") or "(sin targetNamespace)"
    return None, tns


# Mapeo de archivos del ZIP SUNAT (path adentro del ZIP) a path final
# en sunat-1.0/. El ZIP trae UBL 2.0 + extensiones SUNAT (UBLPE-*).
# Tambien trae una copia de UBL 2.1 puro que ignoramos (ya viene de OASIS).
SUNAT_ENTRIES: list[tuple[str, str]] = [
    # maindoc/ — CPE peruanos UBL 2.0 + extensiones SUNAT
    ("Archivos XSD/2.0/maindoc/UBLPE-Retention-1.0.xsd", "maindoc/UBLPE-Retention-1.0.xsd"),
    ("Archivos XSD/2.0/maindoc/UBLPE-Perception-1.0.xsd", "maindoc/UBLPE-Perception-1.0.xsd"),
    (
        "Archivos XSD/2.0/maindoc/UBLPE-SummaryDocuments-1.0.xsd",
        "maindoc/UBLPE-SummaryDocuments-1.0.xsd",
    ),
    (
        "Archivos XSD/2.0/maindoc/UBLPE-VoidedDocuments-1.0.xsd",
        "maindoc/UBLPE-VoidedDocuments-1.0.xsd",
    ),
    (
        "Archivos XSD/2.0/maindoc/UBLPE-ApplicationResponse-1.0.xsd",
        "maindoc/UBLPE-ApplicationResponse-1.0.xsd",
    ),
    # common/ — UBL 2.0 base + extensiones SUNAT
    (
        "Archivos XSD/2.0/common/UBL-CommonAggregateComponents-2.0.xsd",
        "common/UBL-CommonAggregateComponents-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBL-CommonBasicComponents-2.0.xsd",
        "common/UBL-CommonBasicComponents-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBL-CommonExtensionComponents-2.0.xsd",
        "common/UBL-CommonExtensionComponents-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBL-CoreComponentParameters-2.0.xsd",
        "common/UBL-CoreComponentParameters-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBL-ExtensionContentDatatype-2.0.xsd",
        "common/UBL-ExtensionContentDatatype-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBL-QualifiedDatatypes-2.0.xsd",
        "common/UBL-QualifiedDatatypes-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UnqualifiedDataTypeSchemaModule-2.0.xsd",
        "common/UnqualifiedDataTypeSchemaModule-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/CCTS_CCT_SchemaModule-2.0.xsd",
        "common/CCTS_CCT_SchemaModule-2.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/CodeList_CurrencyCode_ISO_7_04.xsd",
        "common/CodeList_CurrencyCode_ISO_7_04.xsd",
    ),
    (
        "Archivos XSD/2.0/common/CodeList_LanguageCode_ISO_7_04.xsd",
        "common/CodeList_LanguageCode_ISO_7_04.xsd",
    ),
    (
        "Archivos XSD/2.0/common/CodeList_MIMEMediaTypeCode_IANA_7_04.xsd",
        "common/CodeList_MIMEMediaTypeCode_IANA_7_04.xsd",
    ),
    (
        "Archivos XSD/2.0/common/CodeList_UnitCode_UNECE_7_04.xsd",
        "common/CodeList_UnitCode_UNECE_7_04.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBLPE-SunatAggregateComponents-1.0.xsd",
        "common/UBLPE-SunatAggregateComponents-1.0.xsd",
    ),
    (
        "Archivos XSD/2.0/common/UBLPE-SunatAggregateComponents-1.1.xsd",
        "common/UBLPE-SunatAggregateComponents-1.1.xsd",
    ),
    ("Archivos XSD/2.0/common/xmldsig-core-schema.xsd", "common/xmldsig-core-schema.xsd"),
]


def refresh_oasis() -> tuple[int, int, list[str]]:
    """Devuelve (n_ok, total_bytes, failures)."""
    print(f"[OASIS UBL 2.1] origen: {OASIS_BASE}")
    print(f"[OASIS UBL 2.1] destino: {OASIS_DEST.relative_to(REPO_ROOT)}")
    print(f"[OASIS UBL 2.1] XSDs a refrescar: {len(OASIS_XSDS)}")
    print()
    failures: list[str] = []
    total_bytes = 0
    for subdir, filename in OASIS_XSDS:
        url = f"{OASIS_BASE}/{subdir}/{filename}"
        dest = OASIS_DEST / subdir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"-> {subdir}/{filename}")
        try:
            content = _fetch(url)
        except urllib.error.URLError as e:
            print(f"   ERROR descarga: {e}")
            failures.append(filename)
            continue
        err, tns = _verify(content)
        if err is not None:
            print(f"   ERROR validacion: {err}")
            failures.append(filename)
            continue
        dest.write_bytes(content)
        total_bytes += len(content)
        print(f"   OK ({len(content):,} bytes) ns={tns}")
    return len(OASIS_XSDS) - len(failures), total_bytes, failures


def refresh_sunat() -> tuple[int, int, list[str]]:
    """Devuelve (n_ok, total_bytes, failures)."""
    print()
    print(f"[SUNAT UBL 2.0 + ext] origen: {SUNAT_ZIP_URL}")
    print(f"[SUNAT UBL 2.0 + ext] destino: {SUNAT_DEST.relative_to(REPO_ROOT)}")
    print(f"[SUNAT UBL 2.0 + ext] XSDs a extraer: {len(SUNAT_ENTRIES)}")
    print()
    try:
        zip_bytes = _fetch(SUNAT_ZIP_URL, timeout=120)
    except urllib.error.URLError as e:
        print(f"   ERROR descarga ZIP: {e}")
        return 0, 0, ["zip-download-failed"]
    print(f"   ZIP descargado: {len(zip_bytes):,} bytes")
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        print(f"   ERROR: ZIP corrupto: {e}")
        return 0, 0, ["zip-corrupt"]
    failures: list[str] = []
    total_bytes = 0
    names = set(zf.namelist())
    for src, dst in SUNAT_ENTRIES:
        if src not in names:
            print(f"-> {dst}")
            print(f"   ERROR: {src!r} no esta en el ZIP")
            failures.append(dst)
            continue
        content = zf.read(src)
        err, tns = _verify(content)
        if err is not None:
            print(f"-> {dst}")
            print(f"   ERROR validacion: {err}")
            failures.append(dst)
            continue
        dest = SUNAT_DEST / dst
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        total_bytes += len(content)
        print(f"-> {dst}")
        print(f"   OK ({len(content):,} bytes) ns={tns}")
    zf.close()
    return len(SUNAT_ENTRIES) - len(failures), total_bytes, failures


def main() -> int:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    oasis_ok, oasis_bytes, oasis_fail = refresh_oasis()
    sunat_ok, sunat_bytes, sunat_fail = refresh_sunat()

    print()
    print("=" * 60)
    total_ok = oasis_ok + sunat_ok
    total_bytes = oasis_bytes + sunat_bytes
    failures = oasis_fail + sunat_fail
    if failures:
        print(f"FALLARON {len(failures)}: {', '.join(failures)}")
        print("El bundle queda inconsistente. Revisa la salida y re-corre.")
        return 1
    print(f"OK: {total_ok} XSDs descargados ({total_bytes:,} bytes total)")
    print(f"     - OASIS UBL 2.1:    {oasis_ok} archivos, {oasis_bytes:,} bytes")
    print(f"     - SUNAT UBL 2.0+ext: {sunat_ok} archivos, {sunat_bytes:,} bytes")
    print()
    print("Siguiente:")
    print(
        f"  1. Revisa los cambios: git diff "
        f"{SCHEMAS_DIR.relative_to(REPO_ROOT).as_posix()}"
    )
    print("  2. Si todo bien, commit al repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
