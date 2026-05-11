import os

import pytest
from lxml import etree
from sunat_py import build_invoice_xml, load_cert_from_base64, sign_invoice_xml
from sunat_py.signer.xmldsig import NS_DS, NS_EXT
from signxml import XMLVerifier


def _has_cert() -> bool:
    return bool(os.environ.get("CERT_PFX_BASE64") and os.environ.get("CERT_PASSWORD"))


@pytest.mark.skipif(not _has_cert(), reason="CERT_PFX_BASE64 / CERT_PASSWORD no configurados")
def test_sign_places_signature_in_extension_content(sample_invoice_input):
    bundle = load_cert_from_base64(os.environ["CERT_PFX_BASE64"], os.environ["CERT_PASSWORD"])
    unsigned = build_invoice_xml(sample_invoice_input)
    signed = sign_invoice_xml(unsigned, bundle)

    root = etree.fromstring(signed)
    signature = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/"
        f"{{{NS_EXT}}}ExtensionContent/{{{NS_DS}}}Signature"
    )
    assert signature is not None, "Signature no esta en ExtensionContent"
    assert signature.get("Id") == "SignatureSP"

    root_level_sig = root.find(f"{{{NS_DS}}}Signature")
    assert root_level_sig is None, "Signature no debe quedar como hijo directo del root"


@pytest.mark.skipif(not _has_cert(), reason="CERT_PFX_BASE64 / CERT_PASSWORD no configurados")
def test_signature_verifies_with_cert_publico(sample_invoice_input):
    bundle = load_cert_from_base64(os.environ["CERT_PFX_BASE64"], os.environ["CERT_PASSWORD"])
    unsigned = build_invoice_xml(sample_invoice_input)
    signed = sign_invoice_xml(unsigned, bundle)

    XMLVerifier().verify(signed, x509_cert=bundle.cert_pem)
