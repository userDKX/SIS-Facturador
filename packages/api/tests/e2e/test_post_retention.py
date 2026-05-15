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
def test_post_retention_end_to_end():
    # Caveat MODDATOS: RUC 20000000001 no esta en padron de agentes de
    # retencion, asi que SUNAT respondera fault 1071 ("emisor no autorizado").
    # Eso NO es bug del SDK: el pipeline build/sign/zip/send/parse-fault
    # funciono y la API persiste status=rejected con sunat_code=1071. Para
    # validar code 0 real hace falta un RUC en padron.
    from sis_facturador.main import app

    client = TestClient(app)

    payload = {
        "serie": "R999",
        "numero": 9999,
        "fecha_emision": "2026-05-11",
        "regimen": "01",
        "tasa": "3.00",
        "total_retenido": "35.40",
        "total_pagado": "1144.60",
        "receptor": {
            "tipo_doc": "6",
            "numero_doc": "20100070970",
            "razon_social": "PROVEEDOR TEST SAC",
            "direccion": "AV TEST 123 LIMA",
        },
        "items": [
            {
                "ref_tipo_doc": "01",
                "ref_serie": "F001",
                "ref_numero": 1,
                "ref_fecha_emision": "2026-05-01",
                "ref_moneda": "PEN",
                "ref_total": "1180.00",
                "fecha_pago": "2026-05-11",
                "correlativo_pago": 1,
                "importe_sin_retencion": "1180.00",
                "importe_retencion": "35.40",
                "fecha_retencion": "2026-05-11",
                "importe_neto_pagado": "1144.60",
            },
        ],
    }

    response = client.post("/v1/retentions", json=payload)

    assert response.status_code in (200, 409), response.text
    data = response.json()

    if response.status_code == 200:
        assert data["status"] in {"accepted", "accepted_with_obs", "rejected"}
        assert data["serie"] == "R999"
        assert data["numero"] == 9999
        assert data["regimen"] == "01"
        assert data["total_retenido"] is not None
        assert data["xml_signed_url"] is not None
