from decimal import Decimal

from lxml import etree
from sunat_py import build_creditnote_xml

NS_CN = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


def test_build_creditnote_xml_root_is_credit_note(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_CN}}}CreditNote"


def test_build_creditnote_xml_has_required_tags(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.1"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}ID").text == "FC01-1"
    assert root.find(f"{{{NS_CBC}}}DocumentCurrencyCode").text == "PEN"

    payable = root.find(f"{{{NS_CAC}}}LegalMonetaryTotal/{{{NS_CBC}}}PayableAmount")
    assert Decimal(payable.text) == Decimal("118.00")


def test_build_creditnote_xml_has_discrepancy_response(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    discrepancy = root.find(f"{{{NS_CAC}}}DiscrepancyResponse")
    assert discrepancy is not None, "DiscrepancyResponse es obligatorio en CreditNote"

    ref_id = discrepancy.find(f"{{{NS_CBC}}}ReferenceID")
    response_code = discrepancy.find(f"{{{NS_CBC}}}ResponseCode")
    description = discrepancy.find(f"{{{NS_CBC}}}Description")

    assert ref_id.text == "F001-1"
    assert response_code.text == "01"
    assert description.text == "ANULACION DE LA OPERACION"


def test_build_creditnote_xml_has_billing_reference(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    billing = root.find(f"{{{NS_CAC}}}BillingReference")
    assert billing is not None, "BillingReference es obligatorio en CreditNote"

    ref_id = billing.find(f"{{{NS_CAC}}}InvoiceDocumentReference/{{{NS_CBC}}}ID")
    doc_type = billing.find(f"{{{NS_CAC}}}InvoiceDocumentReference/{{{NS_CBC}}}DocumentTypeCode")
    assert ref_id.text == "F001-1"
    assert doc_type.text == "01"


def test_build_creditnote_xml_uses_credited_quantity(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    line = root.find(f"{{{NS_CAC}}}CreditNoteLine")
    assert line is not None, "Las lineas deben ir en cac:CreditNoteLine, no cac:InvoiceLine"

    qty = line.find(f"{{{NS_CBC}}}CreditedQuantity")
    assert qty is not None, "Cada CreditNoteLine debe llevar cbc:CreditedQuantity"
    assert qty.get("unitCode") == "NIU"
    assert Decimal(qty.text) == Decimal("1")

    invoiced = line.find(f"{{{NS_CBC}}}InvoicedQuantity")
    assert invoiced is None, "CreditNoteLine no debe usar InvoicedQuantity"


def test_build_creditnote_xml_does_not_have_payment_terms(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))
    payment_terms = root.find(f"{{{NS_CAC}}}PaymentTerms")
    assert payment_terms is None, "PaymentTerms aplica solo a Invoice, no a CreditNote"


def test_build_creditnote_xml_leaves_extension_content_empty(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ext_content = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext_content is not None
    assert len(ext_content) == 0, "ExtensionContent debe quedar vacio para que el signer lo llene"


def test_build_creditnote_xml_motivo_letras_in_note(sample_creditnote_input):
    xml = build_creditnote_xml(sample_creditnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    note = root.find(f"{{{NS_CBC}}}Note")
    assert note is not None
    assert note.get("languageLocaleID") == "1000"
    assert "CIENTO DIECIOCHO" in note.text
    assert "SOLES" in note.text
