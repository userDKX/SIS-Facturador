"""Test de integracion de Nota de Credito contra SUNAT beta.

Pipeline completo: build_creditnote_xml -> sign -> pack -> sendBill.
Requiere los mismos envs que test_sunat_beta.py (CERT_PFX_BASE64,
CERT_PASSWORD, SUNAT_RUC, SUNAT_USER, SUNAT_PASSWORD).

La NC referencia una factura ficticia (SUNAT beta no valida la existencia
real del comprobante referenciado, solo valida el formato UBL). Para
validar el enlace real factura->NC ver el e2e del servicio.

Marker `beta` -> corre con `pytest -m beta`.
"""

import os

import pytest
from sunat_py import (
    build_creditnote_xml,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)


@pytest.mark.beta
def test_sendbill_creditnote_against_sunat_beta(sample_creditnote_input, has_beta_envs):
    if not has_beta_envs:
        pytest.skip("Envs beta SUNAT no configurados")

    bundle = load_cert_from_base64(
        os.environ["CERT_PFX_BASE64"],
        os.environ["CERT_PASSWORD"],
    )
    unsigned = build_creditnote_xml(sample_creditnote_input)
    signed = sign_invoice_xml(unsigned, bundle)

    ruc = os.environ["SUNAT_RUC"]
    filename_base = f"{ruc}-07-{sample_creditnote_input.serie}-{sample_creditnote_input.numero}"
    zip_bytes = pack_invoice(signed, filename_base)

    client = build_zeep_client(
        mode="beta",
        ruc=ruc,
        username=os.environ["SUNAT_USER"],
        password=os.environ["SUNAT_PASSWORD"],
    )
    result = send_bill(client, zip_bytes, f"{filename_base}.zip")

    assert result.status in {
        "accepted",
        "accepted_with_obs",
    }, f"SUNAT rechazo: {result.code} - {result.description}"
    assert result.code in {"0", "098"}
    assert result.cdr_xml
