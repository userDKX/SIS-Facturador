"""Validacion del schema CreditNoteCreate (no requiere envs ni BD ni SUNAT)."""

import pytest
from pydantic import ValidationError
from sis_facturador.schemas.credit_note import CreditNoteCreate

_BASE_PAYLOAD = {
    "serie": "FC01",
    "numero": 1,
    "fecha_emision": "2026-05-10",
    "moneda": "PEN",
    "motivo_codigo": "01",
    "motivo_descripcion": "ANULACION DE LA OPERACION",
    "referencia": {
        "tipo_doc": "01",
        "serie": "F001",
        "numero": 1,
    },
    "receptor": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "EMPRESA EJEMPLO SAC",
        "direccion": "AV EJEMPLO 123",
    },
    "lines": [
        {
            "codigo": "P001",
            "descripcion": "Servicio",
            "unidad": "ZZ",
            "cantidad": "1.00",
            "precio_unitario": "100.00",
            "igv_afectacion": "10",
        },
    ],
}


def test_nc_factura_valid():
    nc = CreditNoteCreate.model_validate(_BASE_PAYLOAD)
    assert nc.serie == "FC01"
    assert nc.referencia.tipo_doc == "01"


def test_nc_boleta_valid():
    payload = {**_BASE_PAYLOAD, "serie": "BC01"}
    payload["referencia"] = {"tipo_doc": "03", "serie": "B001", "numero": 1}
    nc = CreditNoteCreate.model_validate(payload)
    assert nc.serie == "BC01"
    assert nc.referencia.tipo_doc == "03"


def test_serie_factura_pero_referencia_boleta_falla():
    payload = {**_BASE_PAYLOAD}
    payload["referencia"] = {"tipo_doc": "03", "serie": "B001", "numero": 1}
    with pytest.raises(ValidationError) as exc:
        CreditNoteCreate.model_validate(payload)
    assert "no corresponde al tipo del comprobante" in str(exc.value)


def test_serie_boleta_pero_referencia_factura_falla():
    payload = {**_BASE_PAYLOAD, "serie": "BC01"}
    with pytest.raises(ValidationError) as exc:
        CreditNoteCreate.model_validate(payload)
    assert "no corresponde al tipo del comprobante" in str(exc.value)


def test_motivo_codigo_invalido_falla():
    payload = {**_BASE_PAYLOAD, "motivo_codigo": "99"}
    with pytest.raises(ValidationError):
        CreditNoteCreate.model_validate(payload)


def test_serie_pattern_invalido_falla():
    payload = {**_BASE_PAYLOAD, "serie": "XX01"}
    with pytest.raises(ValidationError):
        CreditNoteCreate.model_validate(payload)


def test_motivo_descripcion_obligatoria():
    payload = {**_BASE_PAYLOAD, "motivo_descripcion": ""}
    with pytest.raises(ValidationError):
        CreditNoteCreate.model_validate(payload)


def test_lines_no_puede_estar_vacio():
    payload = {**_BASE_PAYLOAD, "lines": []}
    with pytest.raises(ValidationError):
        CreditNoteCreate.model_validate(payload)
