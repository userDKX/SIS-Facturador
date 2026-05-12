from decimal import Decimal

from lxml import etree
from sunat_py import build_debitnote_xml

NS_DN = "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


def test_build_debitnote_xml_root_is_debit_note(sample_debitnote_input):
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_DN}}}DebitNote"


def test_build_debitnote_xml_has_required_tags(sample_debitnote_input):
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.1"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}ID").text == "FD01-1"
    assert root.find(f"{{{NS_CBC}}}DocumentCurrencyCode").text == "PEN"

    payable = root.find(f"{{{NS_CAC}}}RequestedMonetaryTotal/{{{NS_CBC}}}PayableAmount")
    assert Decimal(payable.text) == Decimal("59.00")


def test_build_debitnote_xml_uses_requested_monetary_total(sample_debitnote_input):
    """ND usa RequestedMonetaryTotal, no LegalMonetaryTotal (que es de NC/Invoice)."""
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CAC}}}RequestedMonetaryTotal") is not None
    assert root.find(f"{{{NS_CAC}}}LegalMonetaryTotal") is None


def test_build_debitnote_xml_discrepancy_response_uses_catalog_10(sample_debitnote_input):
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    response_code = root.find(f"{{{NS_CAC}}}DiscrepancyResponse/{{{NS_CBC}}}ResponseCode")
    assert response_code is not None
    assert response_code.text == "01"
    assert "catalogo10" in response_code.get("listURI")
    assert response_code.get("listName") == "Tipo de nota de debito"


def test_build_debitnote_xml_billing_reference_apunta_al_doc_original(sample_debitnote_input):
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    ref_id = root.find(
        f"{{{NS_CAC}}}BillingReference/{{{NS_CAC}}}InvoiceDocumentReference/{{{NS_CBC}}}ID"
    )
    doc_type = root.find(
        f"{{{NS_CAC}}}BillingReference/{{{NS_CAC}}}InvoiceDocumentReference/{{{NS_CBC}}}DocumentTypeCode"
    )
    assert ref_id.text == "F001-1"
    assert doc_type.text == "01"


def test_build_debitnote_xml_uses_debited_quantity(sample_debitnote_input):
    """Las lineas deben ir en cac:DebitNoteLine con cbc:DebitedQuantity, no CreditedQuantity."""
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))

    line = root.find(f"{{{NS_CAC}}}DebitNoteLine")
    assert line is not None, "lineas deben ir en cac:DebitNoteLine"

    qty = line.find(f"{{{NS_CBC}}}DebitedQuantity")
    assert qty is not None, "cada DebitNoteLine debe llevar cbc:DebitedQuantity"
    assert qty.get("unitCode") == "NIU"
    assert Decimal(qty.text) == Decimal("1")

    credited = line.find(f"{{{NS_CBC}}}CreditedQuantity")
    assert credited is None, "DebitNote no debe usar CreditedQuantity (es de NC)"

    invoiced = line.find(f"{{{NS_CBC}}}InvoicedQuantity")
    assert invoiced is None, "DebitNote no debe usar InvoicedQuantity (es de Invoice)"


def test_build_debitnote_xml_leaves_extension_content_empty(sample_debitnote_input):
    xml = build_debitnote_xml(sample_debitnote_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ext_content = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext_content is not None
    assert len(ext_content) == 0
