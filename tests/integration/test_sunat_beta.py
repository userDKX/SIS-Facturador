import pytest

from app.signer.xmldsig import sign_invoice_xml
from app.sunat.client import send_bill
from app.sunat.packager import pack_invoice
from app.ubl.builder import build_invoice_xml


@pytest.mark.beta
def test_sendbill_against_sunat_beta(sample_invoice_input, has_beta_envs):
    if not has_beta_envs:
        pytest.skip("Envs beta SUNAT no configurados")

    from app.config import settings
    from app.security.cert_loader import load_cert

    bundle = load_cert()
    unsigned = build_invoice_xml(sample_invoice_input)
    signed = sign_invoice_xml(unsigned, bundle)

    filename_base = (
        f"{settings.SUNAT_RUC}-01-{sample_invoice_input.serie}-{sample_invoice_input.numero}"
    )
    zip_bytes = pack_invoice(signed, filename_base)

    result = send_bill(zip_bytes, f"{filename_base}.zip")

    assert result.status in {
        "accepted",
        "accepted_with_obs",
    }, f"SUNAT rechazo: {result.code} - {result.description}"
    assert result.code in {"0", "098"}
    assert result.cdr_xml
