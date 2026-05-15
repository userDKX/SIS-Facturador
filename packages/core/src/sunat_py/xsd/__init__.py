"""Validacion XSD client-side de XML UBL antes de firmar/enviar a SUNAT.

Por defecto el SDK confia en SUNAT para rechazar XML mal formado: el CDR
viene con codigo de error y un mensaje. Eso vuelve lento el dev loop y
deja mensajes opacos. Este modulo permite validar localmente contra los
XSD oficiales (UBL 2.1 + extensiones SUNAT) y obtener errores con linea
y XPath antes de tocar la red.

Uso tipico:

    from sunat_py.xsd import validate_invoice, XSDValidationError

    try:
        validate_invoice(xml_bytes)
    except XSDValidationError as e:
        for err in e.errors:
            print(err.path, err.line, err.message)
"""

from sunat_py.xsd.validator import (
    XSDValidationError,
    XSDValidationItem,
    schemas_available,
    validate_creditnote,
    validate_debitnote,
    validate_despatchadvice,
    validate_invoice,
    validate_perception,
    validate_retention,
    validate_signed_xml,
    validate_summary,
    validate_voided,
    validate_xml,
)

__all__ = [
    "XSDValidationError",
    "XSDValidationItem",
    "schemas_available",
    "validate_creditnote",
    "validate_debitnote",
    "validate_despatchadvice",
    "validate_invoice",
    "validate_perception",
    "validate_retention",
    "validate_signed_xml",
    "validate_summary",
    "validate_voided",
    "validate_xml",
]
