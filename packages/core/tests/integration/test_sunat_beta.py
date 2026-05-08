"""Test de integracion contra SUNAT beta.

Prueba el pipeline completo del SDK (build UBL -> firmar -> empacar ->
sendBill) contra el WS real de SUNAT en su entorno de pruebas. Requiere:

- CERT_PFX_BASE64 + CERT_PASSWORD: el cert MODDATOS publico funciona
- SUNAT_RUC + SUNAT_USER + SUNAT_PASSWORD: credenciales SOL del titular
  (con MODDATOS son las publicas: RUC 20000000001, user MODDATOS,
  pass MODDATOS)

Marker `beta` -> corre con `pytest -m beta`. CI lo skipea con
`pytest -m "not beta"` porque no tiene envs configurados.
"""

import os

import pytest
from pe_invoicing import (
    build_invoice_xml,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)


@pytest.mark.beta
def test_sendbill_against_sunat_beta(sample_invoice_input, has_beta_envs):
    if not has_beta_envs:
        pytest.skip("Envs beta SUNAT no configurados")

    bundle = load_cert_from_base64(
        os.environ["CERT_PFX_BASE64"],
        os.environ["CERT_PASSWORD"],
    )
    unsigned = build_invoice_xml(sample_invoice_input)
    signed = sign_invoice_xml(unsigned, bundle)

    ruc = os.environ["SUNAT_RUC"]
    filename_base = f"{ruc}-01-{sample_invoice_input.serie}-{sample_invoice_input.numero}"
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
