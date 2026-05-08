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
)


@pytest.mark.skipif(
    not all(os.environ.get(k) for k in _REQUIRED_ENVS),
    reason=f"Faltan envs para e2e: {_REQUIRED_ENVS}",
)
def test_post_invoice_end_to_end():
    from sis_facturador.main import app

    client = TestClient(app)

    payload = {
        "serie": "F001",
        "numero": 9999,
        "fecha_emision": "2026-05-04",
        "moneda": "PEN",
        "receptor": {
            "tipo_doc": "6",
            "numero_doc": "20100070970",
            "razon_social": "CLIENTE TEST SAC",
            "direccion": "AV TEST 123 LIMA",
        },
        "lines": [
            {
                "codigo": "P001",
                "descripcion": "PRODUCTO TEST",
                "unidad": "NIU",
                "cantidad": "1",
                "precio_unitario": "100.00",
                "igv_afectacion": "10",
            },
        ],
    }

    response = client.post("/v1/invoices", json=payload)

    assert response.status_code in (200, 409), response.text
    data = response.json()

    if response.status_code == 200:
        assert data["status"] in {"accepted", "accepted_with_obs", "rejected"}
        assert data["serie"] == "F001"
        assert data["numero"] == 9999
        assert data["total"] is not None
