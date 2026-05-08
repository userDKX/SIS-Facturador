from decimal import Decimal

from lxml import etree

from app.ubl.builder import build_invoice_xml, compute_totals
from app.ubl.models import InvoiceLine

NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


def test_compute_totals_simple():
    lines = [
        InvoiceLine(
            codigo="A",
            descripcion="A",
            unidad="NIU",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("50.00"),
            igv_afectacion="10",
        ),
    ]
    totals = compute_totals(lines)
    assert totals.subtotal == Decimal("100.00")
    assert totals.igv == Decimal("18.00")
    assert totals.total == Decimal("118.00")


def test_compute_totals_exonerado_no_igv():
    lines = [
        InvoiceLine(
            codigo="A",
            descripcion="A",
            unidad="NIU",
            cantidad=Decimal("3"),
            precio_unitario=Decimal("10.00"),
            igv_afectacion="20",
        ),
    ]
    totals = compute_totals(lines)
    assert totals.subtotal == Decimal("30.00")
    assert totals.igv == Decimal("0.00")
    assert totals.total == Decimal("30.00")


def test_build_invoice_xml_has_required_tags(sample_invoice_input):
    xml = build_invoice_xml(sample_invoice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.1"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}InvoiceTypeCode").text == "01"
    assert root.find(f"{{{NS_CBC}}}ID").text == "F001-1"
    assert root.find(f"{{{NS_CBC}}}DocumentCurrencyCode").text == "PEN"

    payable = root.find(
        f"{{{NS_CAC}}}LegalMonetaryTotal/{{{NS_CBC}}}PayableAmount"
    )
    assert Decimal(payable.text) == Decimal("118.00")


def test_build_invoice_xml_leaves_extension_content_empty(sample_invoice_input):
    xml = build_invoice_xml(sample_invoice_input)
    NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    root = etree.fromstring(xml.encode("utf-8"))
    ext_content = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext_content is not None
    assert len(ext_content) == 0, "ExtensionContent debe quedar vacio para que el signer lo llene"
