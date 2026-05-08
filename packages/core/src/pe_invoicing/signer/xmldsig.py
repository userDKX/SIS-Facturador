from lxml import etree
from signxml import XMLSigner, methods

from pe_invoicing.security.cert_loader import CertBundle

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
SIGNATURE_ID = "SignatureSP"


def sign_invoice_xml(xml: str, bundle: CertBundle) -> bytes:
    """Firma un XML UBL 2.1 con XMLDSig RSA-SHA256.

    SUNAT requiere que <ds:Signature> viva dentro de
    ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent. signxml inserta
    la firma como ultimo hijo del root, asi que la movemos al lugar correcto
    despues de firmar. La transform enveloped-signature remueve la firma
    durante el calculo del digest sin importar donde este ubicada en el doc.
    """
    root = etree.fromstring(xml.encode("utf-8"))

    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )

    signed_root = signer.sign(
        root,
        key=bundle.key_pem,
        cert=bundle.cert_pem,
    )

    signature = signed_root.find(f"{{{NS_DS}}}Signature")
    if signature is None:
        raise RuntimeError("signxml no inserto el elemento ds:Signature en el root")

    signature.set("Id", SIGNATURE_ID)

    ext_content = signed_root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    if ext_content is None:
        raise RuntimeError("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent no encontrado")

    signed_root.remove(signature)
    ext_content.append(signature)

    return etree.tostring(
        signed_root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=False,
    )
