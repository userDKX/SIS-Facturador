"""Validador XSD client-side para XML UBL antes de enviar a SUNAT."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from lxml import etree

from sunat_py.errors import ValidationError

_SCHEMAS_DIR = Path(__file__).parent / "schemas"


# Mapeo logico -> path al XSD raiz, relativo a `schemas/`.
#
# Layout del bundle (lo arma `scripts/refresh_xsd_schemas.py`):
#
#   schemas/
#   |- ubl-2.1/                  OASIS UBL 2.1 — Factura/Boleta/NC/ND/GRE
#   |  |- maindoc/
#   |  `- common/
#   `- sunat-1.0/                SUNAT UBL 2.0 + extensiones — RA/RC/RET/PER
#      |- maindoc/   UBLPE-*-1.0.xsd
#      `- common/    UBL 2.0 common + UBLPE-SunatAggregate
#
# Nota: SUNAT nunca publico version 2.1 de retencion/percepcion/RA/RC.
# Esos CPE quedaron en UBL 2.0 + extensiones peruanas (namespace
# `urn:sunat:names:specification:ubl:peru:schema:xsd:...`).
_ROOT_SCHEMAS: dict[str, str] = {
    "invoice": "ubl-2.1/maindoc/UBL-Invoice-2.1.xsd",
    "creditnote": "ubl-2.1/maindoc/UBL-CreditNote-2.1.xsd",
    "debitnote": "ubl-2.1/maindoc/UBL-DebitNote-2.1.xsd",
    "despatchadvice": "ubl-2.1/maindoc/UBL-DespatchAdvice-2.1.xsd",
    "summary": "sunat-1.0/maindoc/UBLPE-SummaryDocuments-1.0.xsd",
    "voided": "sunat-1.0/maindoc/UBLPE-VoidedDocuments-1.0.xsd",
    "retention": "sunat-1.0/maindoc/UBLPE-Retention-1.0.xsd",
    "perception": "sunat-1.0/maindoc/UBLPE-Perception-1.0.xsd",
}


@dataclass(frozen=True)
class XSDValidationItem:
    """Un error individual del schema validator."""

    message: str
    line: int
    path: str
    domain: str
    type_name: str


class XSDValidationError(ValidationError):
    """El XML no valida contra el XSD oficial SUNAT.

    Lleva la lista completa de errores reportados por lxml para que el
    consumidor pueda inspeccionarlos. El mensaje principal resume el
    primer error (que suele ser la causa raiz; los demas son cascada).
    """

    def __init__(self, errors: list[XSDValidationItem], schema: str) -> None:
        self.errors = errors
        self.schema = schema
        if errors:
            first = errors[0]
            summary = f"XSD {schema}: {first.message} (linea {first.line}, {first.path})"
            if len(errors) > 1:
                summary += f" [+{len(errors) - 1} mas]"
        else:
            summary = f"XSD {schema}: validacion fallida sin detalle"
        super().__init__(summary)


@cache
def _load_schema(filename: str) -> etree.XMLSchema:
    """Carga y cachea un XMLSchema desde `schemas/`.

    Lazy: la primera llamada parsea el XSD; las siguientes devuelven el
    objeto cacheado. lxml.etree.XMLSchema es thread-safe para validacion.
    """
    path = _SCHEMAS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"XSD '{filename}' no esta bundleado en sunat_py.xsd.schemas. "
            f"Instala los XSDs oficiales (ver sunat_py/xsd/schemas/README.md) "
            f"o llama a las funciones build_*_xml con validate=False."
        )
    # parser con base_url para que los <xs:import schemaLocation="..."/>
    # relativos resuelvan contra _SCHEMAS_DIR.
    parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
    schema_doc = etree.parse(str(path), parser)
    return etree.XMLSchema(schema_doc)


def schemas_available() -> bool:
    """True si todos los XSDs raiz estan bundleados.

    Util para tests/CI: permite saltar tests de regresion si el bundle
    aun no fue agregado al repo.
    """
    return all((_SCHEMAS_DIR / fn).exists() for fn in _ROOT_SCHEMAS.values())


def _collect_errors(schema: etree.XMLSchema) -> list[XSDValidationItem]:
    return [
        XSDValidationItem(
            message=err.message or "",
            line=err.line or 0,
            path=err.path or "",
            domain=err.domain_name or "",
            type_name=err.type_name or "",
        )
        for err in schema.error_log
    ]


def validate_xml(xml: str | bytes, kind: str) -> None:
    """Valida `xml` contra el XSD logico `kind` (invoice, creditnote, ...).

    Raises:
        XSDValidationError: si el documento no valida.
        ValueError: si `kind` no es uno de los soportados.
        FileNotFoundError: si el XSD no esta bundleado.
        etree.XMLSyntaxError: si el XML no es well-formed.
    """
    if kind not in _ROOT_SCHEMAS:
        raise ValueError(
            f"kind {kind!r} desconocido. Validos: {sorted(_ROOT_SCHEMAS)}"
        )
    schema = _load_schema(_ROOT_SCHEMAS[kind])

    if isinstance(xml, str):
        xml = xml.encode("utf-8")

    parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
    doc = etree.fromstring(xml, parser=parser)

    if not schema.validate(doc):
        raise XSDValidationError(_collect_errors(schema), schema=kind)


# Mapeo del local-name del root element -> kind logico. Permite
# validar XML firmado sin que el caller tenga que recordar el kind.
_ROOT_TAG_TO_KIND: dict[str, str] = {
    "Invoice": "invoice",
    "CreditNote": "creditnote",
    "DebitNote": "debitnote",
    "DespatchAdvice": "despatchadvice",
    "SummaryDocuments": "summary",
    "VoidedDocuments": "voided",
    "Retention": "retention",
    "Perception": "perception",
}


def validate_signed_xml(xml: str | bytes) -> None:
    """Valida un XML firmado, infiriendo el kind del root element.

    Pensado para el pipeline post-firma: el caller ya tiene el XML con
    `<ds:Signature>` adentro y solo quiere "gate XSD antes de empaquetar
    y enviar a SUNAT".

    Raises:
        ValueError: si el root no es uno de los CPE conocidos.
        El resto: igual que `validate_xml`.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")

    parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
    doc = etree.fromstring(xml, parser=parser)

    local = etree.QName(doc.tag).localname
    if local not in _ROOT_TAG_TO_KIND:
        raise ValueError(
            f"root element {local!r} no es un CPE conocido. "
            f"Validos: {sorted(_ROOT_TAG_TO_KIND)}"
        )

    kind = _ROOT_TAG_TO_KIND[local]
    schema = _load_schema(_ROOT_SCHEMAS[kind])

    if not schema.validate(doc):
        raise XSDValidationError(_collect_errors(schema), schema=kind)


def validate_invoice(xml: str | bytes) -> None:
    """Valida una factura o boleta (UBL Invoice 2.1)."""
    validate_xml(xml, "invoice")


def validate_creditnote(xml: str | bytes) -> None:
    """Valida una nota de credito (UBL CreditNote 2.1)."""
    validate_xml(xml, "creditnote")


def validate_debitnote(xml: str | bytes) -> None:
    """Valida una nota de debito (UBL DebitNote 2.1)."""
    validate_xml(xml, "debitnote")


def validate_despatchadvice(xml: str | bytes) -> None:
    """Valida una guia de remision (UBL DespatchAdvice 2.1)."""
    validate_xml(xml, "despatchadvice")


def validate_summary(xml: str | bytes) -> None:
    """Valida un resumen diario de boletas (RC, SUNAT SummaryDocuments-1)."""
    validate_xml(xml, "summary")


def validate_voided(xml: str | bytes) -> None:
    """Valida una comunicacion de baja (RA, SUNAT VoidedDocuments-1)."""
    validate_xml(xml, "voided")


def validate_retention(xml: str | bytes) -> None:
    """Valida un comprobante de retencion (tipo 20, SUNAT Retention-1)."""
    validate_xml(xml, "retention")


def validate_perception(xml: str | bytes) -> None:
    """Valida un comprobante de percepcion (tipo 40, SUNAT Perception-1)."""
    validate_xml(xml, "perception")
