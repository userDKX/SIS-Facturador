import os

import pytest
from lxml import etree
from signxml import XMLVerifier

from app.signer.xmldsig import NS_DS, NS_EXT, sign_invoice_xml
from app.ubl.builder import build_invoice_xml


@pytest.mark.skipif(
    not (os.environ.get("CERT_PFX_BASE64") and os.environ.get("CERT_PASSWORD")),
    reason="CERT_PFX_BASE64 / CERT_PASSWORD no configurados",
)
def test_sign_places_signature_in_extension_content(sample_invoice_input):
    from app.security.cert_loader import load_cert

    bundle = load_cert()
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


@pytest.mark.skipif(
    not (os.environ.get("CERT_PFX_BASE64") and os.environ.get("CERT_PASSWORD")),
    reason="CERT_PFX_BASE64 / CERT_PASSWORD no configurados",
)
def test_signature_verifies_with_cert_publico(sample_invoice_input):
    from app.security.cert_loader import load_cert

    bundle = load_cert()
    unsigned = build_invoice_xml(sample_invoice_input)
    signed = sign_invoice_xml(unsigned, bundle)

    XMLVerifier().verify(signed, x509_cert=bundle.cert_pem)
