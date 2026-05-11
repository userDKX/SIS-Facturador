import os

import pytest
from fastapi.testclient import TestClient

_REQUIRED_ENVS = (
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "CERT_PFX_BASE64",
    "CERT_PASSWORD",
    "SUNAT_RUC",
    "SUNAT_USER",
    "SUNAT_PASSWORD",
    "GRE_CLIENT_ID",
    "GRE_CLIENT_SECRET",
)


@pytest.mark.skipif(
    not all(os.environ.get(k) for k in _REQUIRED_ENVS),
    reason=f"Faltan envs para e2e: {_REQUIRED_ENVS}",
)
def test_post_despatch_advice_end_to_end():
    from sis_facturador.main import app

    client = TestClient(app)

    payload = {
        "serie": "T001",
        "numero": 9999,
        "fecha_emision": "2026-05-11",
        "motivo_traslado": "01",
        "motivo_descripcion": "VENTA",
        "modalidad": "02",
        "peso_bruto_total": "10.00",
        "peso_bruto_unidad": "KGM",
        "numero_bultos": 1,
        "destinatario": {
            "tipo_doc": "6",
            "numero_doc": "20100070970",
            "razon_social": "CLIENTE TEST SAC",
            "direccion": "AV CLIENTE 456 LIMA",
        },
        "partida": {"ubigeo": "150101", "direccion": "AV TEST 123 LIMA", "cod_local": "0000"},
        "llegada": {"ubigeo": "150122", "direccion": "AV CLIENTE 456 LIMA"},
        "conductor": {
            "tipo_doc": "1",
            "numero_doc": "12345678",
            "nombres": "JUAN",
            "apellidos": "PEREZ",
            "licencia": "Q12345678",
        },
        "vehiculo": {"placa": "ABC123"},
        "lines": [
            {"codigo": "P001", "descripcion": "PRODUCTO TEST", "unidad": "NIU", "cantidad": "5"},
        ],
    }

    response = client.post("/v1/despatch-advices", json=payload)

    assert response.status_code in (200, 409), response.text
    data = response.json()

    if response.status_code == 200:
        assert data["status"] in {"accepted", "accepted_with_obs", "rejected"}
        assert data["serie"] == "T001"
        assert data["numero"] == 9999
        assert data["motivo_traslado"] == "01"
        assert data["vehiculo_placa"] == "ABC123"
