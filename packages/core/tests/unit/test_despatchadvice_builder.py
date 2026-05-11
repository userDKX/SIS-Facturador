from decimal import Decimal

from lxml import etree
from pe_invoicing import build_despatchadvice_xml

NS_DA = "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


def test_build_despatchadvice_xml_root_is_despatch_advice(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_DA}}}DespatchAdvice"


def test_build_despatchadvice_xml_has_required_tags(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.1"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}ID").text == "T001-1"

    type_code = root.find(f"{{{NS_CBC}}}DespatchAdviceTypeCode")
    assert type_code is not None
    assert type_code.text == "09"


def test_build_despatchadvice_xml_has_shipment(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    shipment = root.find(f"{{{NS_CAC}}}Shipment")
    assert shipment is not None, "Shipment es obligatorio en DespatchAdvice"

    handling_code = shipment.find(f"{{{NS_CBC}}}HandlingCode")
    assert handling_code.text == "01"

    weight = shipment.find(f"{{{NS_CBC}}}GrossWeightMeasure")
    assert weight is not None
    assert weight.get("unitCode") == "KGM"
    assert Decimal(weight.text) == Decimal("10.00")


def test_build_despatchadvice_xml_has_origin_and_delivery(sample_despatchadvice_input):
    """SUNAT GRE 2.0: partida va en cac:Delivery/cac:Despatch/cac:DespatchAddress
    (no en cac:OriginAddress como UBL puro)."""
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    shipment = root.find(f"{{{NS_CAC}}}Shipment")

    delivery = shipment.find(f"{{{NS_CAC}}}Delivery/{{{NS_CAC}}}DeliveryAddress")
    assert delivery is not None
    assert delivery.find(f"{{{NS_CBC}}}ID").text == "150122"

    despatch = shipment.find(f"{{{NS_CAC}}}Delivery/{{{NS_CAC}}}Despatch/{{{NS_CAC}}}DespatchAddress")
    assert despatch is not None
    assert despatch.find(f"{{{NS_CBC}}}ID").text == "150101"
    # cod_local del fixture: "0000" - se emite como cbc:AddressTypeCode con listID=RUC.
    type_code = despatch.find(f"{{{NS_CBC}}}AddressTypeCode")
    assert type_code is not None
    assert type_code.text == "0000"


def test_build_despatchadvice_xml_private_transport_has_driver_and_vehicle(
    sample_despatchadvice_input,
):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    shipment = root.find(f"{{{NS_CAC}}}Shipment")
    stage = shipment.find(f"{{{NS_CAC}}}ShipmentStage")
    assert stage is not None

    mode = stage.find(f"{{{NS_CBC}}}TransportModeCode")
    assert mode.text == "02"

    driver = stage.find(f"{{{NS_CAC}}}DriverPerson")
    assert driver is not None
    assert driver.find(f"{{{NS_CBC}}}ID").text == "12345678"

    vehicle = shipment.find(f"{{{NS_CAC}}}TransportHandlingUnit/{{{NS_CAC}}}TransportEquipment/{{{NS_CBC}}}ID")
    assert vehicle is not None
    assert vehicle.text == "ABC123"


def test_build_despatchadvice_xml_has_numero_bultos(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    shipment = root.find(f"{{{NS_CAC}}}Shipment")
    bultos = shipment.find(f"{{{NS_CBC}}}TotalTransportHandlingUnitQuantity")
    assert bultos is not None
    assert bultos.text == "2"


def test_build_despatchadvice_xml_has_despatch_lines(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    lines = root.findall(f"{{{NS_CAC}}}DespatchLine")
    assert len(lines) == 1

    qty = lines[0].find(f"{{{NS_CBC}}}DeliveredQuantity")
    assert qty is not None
    assert qty.get("unitCode") == "NIU"
    assert Decimal(qty.text) == Decimal("5")

    desc = lines[0].find(f"{{{NS_CAC}}}Item/{{{NS_CBC}}}Description")
    assert desc.text == "PRODUCTO TEST"


def test_build_despatchadvice_xml_no_tax_or_monetary_totals(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    assert root.find(f"{{{NS_CAC}}}TaxTotal") is None, "GR no debe tener TaxTotal"
    assert root.find(f"{{{NS_CAC}}}LegalMonetaryTotal") is None, "GR no debe tener LegalMonetaryTotal"


def test_build_despatchadvice_xml_leaves_extension_content_empty(sample_despatchadvice_input):
    xml = build_despatchadvice_xml(sample_despatchadvice_input)
    root = etree.fromstring(xml.encode("utf-8"))

    ext_content = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext_content is not None
    assert len(ext_content) == 0


def test_build_despatchadvice_xml_public_transport_has_carrier(sample_despatchadvice_input):
    """Reemplaza conductor/vehiculo por transportista para modalidad 01."""
    from pe_invoicing import DespatchAdviceInput, Transportista

    inv = DespatchAdviceInput(
        serie=sample_despatchadvice_input.serie,
        numero=sample_despatchadvice_input.numero,
        fecha_emision=sample_despatchadvice_input.fecha_emision,
        motivo_traslado=sample_despatchadvice_input.motivo_traslado,
        motivo_descripcion=sample_despatchadvice_input.motivo_descripcion,
        modalidad="01",
        peso_bruto_total=sample_despatchadvice_input.peso_bruto_total,
        peso_bruto_unidad=sample_despatchadvice_input.peso_bruto_unidad,
        emisor=sample_despatchadvice_input.emisor,
        destinatario=sample_despatchadvice_input.destinatario,
        partida=sample_despatchadvice_input.partida,
        llegada=sample_despatchadvice_input.llegada,
        lines=sample_despatchadvice_input.lines,
        transportista=Transportista(numero_doc="20100123456", razon_social="TRANSPORTES SAC"),
    )
    xml = build_despatchadvice_xml(inv)
    root = etree.fromstring(xml.encode("utf-8"))

    shipment = root.find(f"{{{NS_CAC}}}Shipment")
    stage = shipment.find(f"{{{NS_CAC}}}ShipmentStage")

    mode = stage.find(f"{{{NS_CBC}}}TransportModeCode")
    assert mode.text == "01"

    carrier = stage.find(f"{{{NS_CAC}}}CarrierParty")
    assert carrier is not None
    carrier_ruc = carrier.find(f"{{{NS_CAC}}}PartyIdentification/{{{NS_CBC}}}ID")
    assert carrier_ruc.text == "20100123456"
