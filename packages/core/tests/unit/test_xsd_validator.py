"""Tests del validador XSD con schemas sinteticos.

No requieren los XSDs oficiales bundleados: cada test arma un XSD
minimo en tmp_path y monkey-patchea `_SCHEMAS_DIR` para apuntar ahi.
Asi validamos la mecanica (lru_cache, error collection, kind mapping)
sin depender del paquete de schemas SUNAT.
"""

from __future__ import annotations

import pytest
from sunat_py.xsd import (
    XSDValidationError,
    schemas_available,
    validate_invoice,
    validate_xml,
)
from sunat_py.xsd import validator as xsd_validator

_SCHEMA_DUMMY_INVOICE = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="urn:test:invoice"
           xmlns="urn:test:invoice"
           elementFormDefault="qualified">
  <xs:element name="Invoice">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="ID" type="xs:string"/>
        <xs:element name="Total" type="xs:decimal"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


@pytest.fixture
def fake_schemas_dir(tmp_path, monkeypatch):
    """Apunta `_SCHEMAS_DIR` a tmp y limpia el cache de lru_cache.

    El XSD dummy se ubica en `ubl-2.1/maindoc/UBL-Invoice-2.1.xsd` para
    coincidir con la ruta declarada en `_ROOT_SCHEMAS['invoice']`.
    """
    schema_path = tmp_path / "ubl-2.1" / "maindoc" / "UBL-Invoice-2.1.xsd"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(_SCHEMA_DUMMY_INVOICE, encoding="utf-8")
    monkeypatch.setattr(xsd_validator, "_SCHEMAS_DIR", tmp_path)
    xsd_validator._load_schema.cache_clear()
    yield tmp_path
    xsd_validator._load_schema.cache_clear()


def test_validate_invoice_ok(fake_schemas_dir):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Invoice xmlns="urn:test:invoice"><ID>F001-1</ID>'
        "<Total>118.00</Total></Invoice>"
    )
    validate_invoice(xml)


def test_validate_invoice_missing_required_element_raises(fake_schemas_dir):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Invoice xmlns="urn:test:invoice"><ID>F001-1</ID></Invoice>'
    )
    with pytest.raises(XSDValidationError) as exc:
        validate_invoice(xml)
    assert exc.value.schema == "invoice"
    assert exc.value.errors
    assert exc.value.errors[0].line > 0
    assert "Total" in exc.value.errors[0].message


def test_validate_invoice_wrong_type_raises(fake_schemas_dir):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Invoice xmlns="urn:test:invoice"><ID>F001-1</ID>'
        "<Total>no-decimal</Total></Invoice>"
    )
    with pytest.raises(XSDValidationError):
        validate_invoice(xml)


def test_validate_xml_kind_invalido():
    with pytest.raises(ValueError, match="kind 'nope' desconocido"):
        validate_xml("<x/>", "nope")


def test_validate_xml_falta_xsd_bundleado(tmp_path, monkeypatch):
    """Si el archivo XSD no existe, FileNotFoundError con mensaje claro."""
    monkeypatch.setattr(xsd_validator, "_SCHEMAS_DIR", tmp_path)
    xsd_validator._load_schema.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="no esta bundleado"):
            validate_invoice("<Invoice/>")
    finally:
        xsd_validator._load_schema.cache_clear()


def test_validate_xml_acepta_bytes(fake_schemas_dir):
    xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<Invoice xmlns="urn:test:invoice"><ID>F001-1</ID>'
        b"<Total>118.00</Total></Invoice>"
    )
    validate_invoice(xml)


def test_xsd_validation_error_es_validation_error():
    """XSDValidationError hereda de ValidationError (jerarquia del SDK)."""
    from sunat_py.errors import ValidationError

    assert issubclass(XSDValidationError, ValidationError)


def test_schemas_available_false_sin_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(xsd_validator, "_SCHEMAS_DIR", tmp_path)
    assert schemas_available() is False


def test_schemas_available_true_con_bundle_completo(tmp_path, monkeypatch):
    for filename in xsd_validator._ROOT_SCHEMAS.values():
        target = tmp_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("<dummy/>", encoding="utf-8")
    monkeypatch.setattr(xsd_validator, "_SCHEMAS_DIR", tmp_path)
    assert schemas_available() is True


def test_load_schema_cachea(fake_schemas_dir):
    """Segunda llamada al mismo filename retorna el mismo objeto cacheado."""
    s1 = xsd_validator._load_schema("ubl-2.1/maindoc/UBL-Invoice-2.1.xsd")
    s2 = xsd_validator._load_schema("ubl-2.1/maindoc/UBL-Invoice-2.1.xsd")
    assert s1 is s2


def test_xsd_validation_error_resumen_lleva_primer_error(fake_schemas_dir):
    """El str() de la excepcion debe ser legible (linea + path + primer mensaje)."""
    xml = '<Invoice xmlns="urn:test:invoice"><ID>F001-1</ID></Invoice>'
    with pytest.raises(XSDValidationError) as exc:
        validate_invoice(xml)
    msg = str(exc.value)
    assert "XSD invoice" in msg
    assert "linea" in msg


# Los tests de regresion contra XML real (firmado) del SDK viven en
# test_signed_xml_xsd.py — se ejecutan despues de firmar, porque el XML
# pre-firma tiene <ext:ExtensionContent/> vacio y por diseno UBL falla
# XSD validation hasta que el signer rellena ese hueco.
