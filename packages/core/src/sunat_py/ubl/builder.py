from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree

from sunat_py.errors import ValidationError
from sunat_py.ubl.models import (
    CreditNoteInput,
    DebitNoteInput,
    DespatchAdviceInput,
    GRLine,
    InvoiceInput,
    InvoiceLine,
    InvoiceTotals,
    RetentionInput,
    SummaryDocumentsInput,
    VoidedDocumentsInput,
)
from sunat_py.validators import (
    validate_emisor,
    validate_emission_date,
    validate_identity_doc,
    validate_lines,
    validate_retention,
)

IGV_RATE = Decimal("0.18")
TWO_DP = Decimal("0.01")

CURRENCY_NAMES = {
    "PEN": ("SOLES", "SOL"),
    "USD": ("DOLARES AMERICANOS", "DOLAR AMERICANO"),
    "EUR": ("EUROS", "EURO"),
}

_UNIDADES = [
    "",
    "UNO",
    "DOS",
    "TRES",
    "CUATRO",
    "CINCO",
    "SEIS",
    "SIETE",
    "OCHO",
    "NUEVE",
    "DIEZ",
    "ONCE",
    "DOCE",
    "TRECE",
    "CATORCE",
    "QUINCE",
    "DIECISEIS",
    "DIECISIETE",
    "DIECIOCHO",
    "DIECINUEVE",
    "VEINTE",
]
_DECENAS = [
    "",
    "",
    "VEINTI",
    "TREINTA",
    "CUARENTA",
    "CINCUENTA",
    "SESENTA",
    "SETENTA",
    "OCHENTA",
    "NOVENTA",
]
_CENTENAS = [
    "",
    "CIENTO",
    "DOSCIENTOS",
    "TRESCIENTOS",
    "CUATROCIENTOS",
    "QUINIENTOS",
    "SEISCIENTOS",
    "SETECIENTOS",
    "OCHOCIENTOS",
    "NOVECIENTOS",
]


def _hasta_999(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    centenas = n // 100
    resto = n % 100
    parts = []
    if centenas:
        parts.append(_CENTENAS[centenas])
    if resto <= 20:
        if resto:
            parts.append(_UNIDADES[resto])
    elif resto < 30:
        unidad = resto - 20
        parts.append(f"VEINTI{_UNIDADES[unidad]}" if unidad else "VEINTE")
    else:
        decenas = resto // 10
        unidad = resto % 10
        if unidad:
            parts.append(f"{_DECENAS[decenas]} Y {_UNIDADES[unidad]}")
        else:
            parts.append(_DECENAS[decenas].rstrip())
    return " ".join(p for p in parts if p)


def _numero_a_letras(entero: int) -> str:
    if entero == 0:
        return "CERO"
    if entero < 0:
        return f"MENOS {_numero_a_letras(-entero)}"
    millones = entero // 1_000_000
    miles = (entero % 1_000_000) // 1000
    resto = entero % 1000
    parts = []
    if millones:
        if millones == 1:
            parts.append("UN MILLON")
        else:
            parts.append(f"{_hasta_999(millones)} MILLONES")
    if miles:
        if miles == 1:
            parts.append("MIL")
        else:
            parts.append(f"{_hasta_999(miles)} MIL")
    if resto:
        parts.append(_hasta_999(resto))
    return " ".join(parts)


def monto_en_letras(total: Decimal, moneda: str) -> str:
    """SUNAT cat. 7 codigo 1000 - monto en letras."""
    plural, _ = CURRENCY_NAMES.get(moneda, (moneda, moneda))
    entero = int(total)
    centavos = int((total - entero).quantize(TWO_DP, rounding=ROUND_HALF_UP) * 100)
    letras = _numero_a_letras(entero)
    return f"SON {letras} CON {centavos:02d}/100 {plural}"


_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("xml", "j2"), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _q(value: Decimal) -> str:
    return str(value.quantize(TWO_DP, rounding=ROUND_HALF_UP))


def _quant(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def compute_totals(lines: list[InvoiceLine]) -> InvoiceTotals:
    subtotal = Decimal("0")
    igv = Decimal("0")
    for line in lines:
        line_base = _quant(line.cantidad * line.precio_unitario)
        subtotal += line_base
        if line.igv_afectacion == "10":
            igv += _quant(line_base * IGV_RATE)
    total = subtotal + igv
    return InvoiceTotals(
        subtotal=_quant(subtotal),
        igv=_quant(igv),
        total=_quant(total),
    )


def _enrich_line(line: InvoiceLine, moneda: str) -> dict:
    """Pre-calcula campos derivados para mantener simple la plantilla."""
    base = _quant(line.cantidad * line.precio_unitario)

    if line.igv_afectacion == "10":
        line_igv = _quant(base * IGV_RATE)
        precio_con_igv = _quant(line.precio_unitario * (Decimal("1") + IGV_RATE))
        igv_percent = "18.00"
        tax_scheme_id = "1000"
        tax_scheme_name = "IGV"
        tax_scheme_type = "VAT"
    elif line.igv_afectacion == "20":  # exonerado
        line_igv = Decimal("0.00")
        precio_con_igv = _quant(line.precio_unitario)
        igv_percent = "0.00"
        tax_scheme_id = "9997"
        tax_scheme_name = "EXO"
        tax_scheme_type = "VAT"
    else:  # inafecto u otros
        line_igv = Decimal("0.00")
        precio_con_igv = _quant(line.precio_unitario)
        igv_percent = "0.00"
        tax_scheme_id = "9998"
        tax_scheme_name = "INA"
        tax_scheme_type = "FRE"

    return {
        "codigo": line.codigo,
        "descripcion": line.descripcion,
        "unidad": line.unidad,
        "cantidad": str(line.cantidad),
        "precio_unitario": _q(line.precio_unitario),
        "precio_con_igv": str(precio_con_igv),
        "subtotal": str(base),
        "igv": str(line_igv),
        "igv_afectacion": line.igv_afectacion,
        "igv_percent": igv_percent,
        "tax_scheme_id": tax_scheme_id,
        "tax_scheme_name": tax_scheme_name,
        "tax_scheme_type": tax_scheme_type,
    }


def build_invoice_xml(inv: InvoiceInput) -> str:
    """Renderiza un Invoice UBL 2.1 sin firmar.

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    validate_identity_doc(inv.receptor.tipo_doc, inv.receptor.numero_doc)
    validate_emission_date(inv.fecha_emision)
    validate_lines(inv.lines)

    template = _env.get_template("invoice_01.xml.j2")
    totals = compute_totals(inv.lines)
    enriched_lines = [_enrich_line(line, inv.moneda) for line in inv.lines]

    rendered = template.render(
        inv=inv,
        lines=enriched_lines,
        totals={
            "subtotal": _q(totals.subtotal),
            "igv": _q(totals.igv),
            "total": _q(totals.total),
            "monto_letras": monto_en_letras(totals.total, inv.moneda),
        },
    )

    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def build_creditnote_xml(inv: CreditNoteInput) -> str:
    """Renderiza una CreditNote UBL 2.1 (tipo 07) sin firmar.

    Diferencias UBL respecto a Invoice:
      * Root <CreditNote> con namespace propio (CreditNote-2).
      * <cac:DiscrepancyResponse> con motivo del catalogo 09.
      * <cac:BillingReference> apuntando al doc original (factura o boleta).
      * Lineas en <cac:CreditNoteLine> con <cbc:CreditedQuantity>.
      * Sin <cac:PaymentTerms> (no aplica a notas).

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    validate_identity_doc(inv.receptor.tipo_doc, inv.receptor.numero_doc)
    validate_emission_date(inv.fecha_emision)
    validate_lines(inv.lines)

    template = _env.get_template("creditnote_07.xml.j2")
    totals = compute_totals(inv.lines)
    enriched_lines = [_enrich_line(line, inv.moneda) for line in inv.lines]

    rendered = template.render(
        inv=inv,
        lines=enriched_lines,
        totals={
            "subtotal": _q(totals.subtotal),
            "igv": _q(totals.igv),
            "total": _q(totals.total),
            "monto_letras": monto_en_letras(totals.total, inv.moneda),
        },
    )

    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def build_debitnote_xml(inv: DebitNoteInput) -> str:
    """Renderiza una DebitNote UBL 2.1 (tipo 08) sin firmar.

    Diferencias UBL respecto a CreditNote:
      * Root <DebitNote> con namespace DebitNote-2.
      * <cac:DiscrepancyResponse> con motivo del catalogo 10 (no 09).
      * <cac:RequestedMonetaryTotal> en lugar de <cac:LegalMonetaryTotal>.
      * Lineas en <cac:DebitNoteLine> con <cbc:DebitedQuantity>.

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    validate_identity_doc(inv.receptor.tipo_doc, inv.receptor.numero_doc)
    validate_emission_date(inv.fecha_emision)
    validate_lines(inv.lines)

    template = _env.get_template("debitnote_08.xml.j2")
    totals = compute_totals(inv.lines)
    enriched_lines = [_enrich_line(line, inv.moneda) for line in inv.lines]

    rendered = template.render(
        inv=inv,
        lines=enriched_lines,
        totals={
            "subtotal": _q(totals.subtotal),
            "igv": _q(totals.igv),
            "total": _q(totals.total),
            "monto_letras": monto_en_letras(totals.total, inv.moneda),
        },
    )

    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def build_voided_xml(inv: VoidedDocumentsInput) -> str:
    """Renderiza una comunicacion de baja (RA) UBL sin firmar.

    Estructura UBL especifica de SUNAT (namespace sunat: VoidedDocuments-1):
      * Sin TaxTotal ni MonetaryTotal (no maneja dinero).
      * <cbc:ReferenceDate> = fecha del CPE a anular.
      * <cbc:IssueDate> = fecha de envio del RA.
      * <sac:VoidedDocumentsLine> por cada CPE a anular.

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    if not inv.items:
        raise ValidationError("RA: items no puede estar vacio")
    for idx, item in enumerate(inv.items, start=1):
        if not item.motivo:
            raise ValidationError(f"RA item {idx}: motivo es obligatorio")
        if item.tipo_doc not in {"01", "03", "07", "08"}:
            raise ValidationError(
                f"RA item {idx}: tipo_doc {item.tipo_doc!r} invalido "
                f"(validos: 01 factura, 03 boleta, 07 NC, 08 ND)"
            )

    template = _env.get_template("voided_RA.xml.j2")
    rendered = template.render(inv=inv)
    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def _enrich_summary_item(item) -> dict:
    return {
        "tipo_doc": item.tipo_doc,
        "serie": item.serie,
        "numero": item.numero,
        "cliente_tipo_doc": item.cliente_tipo_doc,
        "cliente_numero_doc": item.cliente_numero_doc,
        "moneda": item.moneda,
        "total": _q(item.total),
        "base_gravada": _q(item.base_gravada),
        "igv": _q(item.igv),
        "estado": item.estado,
        "base_exonerada": _q(item.base_exonerada) if item.base_exonerada else None,
        "base_inafecta": _q(item.base_inafecta) if item.base_inafecta else None,
    }


def build_summary_xml(inv: SummaryDocumentsInput) -> str:
    """Renderiza un resumen diario de boletas (RC) UBL sin firmar.

    Estructura UBL especifica de SUNAT (namespace sunat: SummaryDocuments-1):
      * <cbc:ReferenceDate> = fecha de las boletas resumidas.
      * <cbc:IssueDate> = fecha de envio del RC.
      * <sac:SummaryDocumentsLine> por cada boleta/NC/ND incluida.
      * Cada linea lleva cliente (tipo_doc + numero), total, base
        gravada/exonerada/inafecta, IGV, y estado (1 adicionar,
        2 modificar, 3 anular).

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    if not inv.items:
        raise ValidationError("RC: items no puede estar vacio")
    for idx, item in enumerate(inv.items, start=1):
        if item.tipo_doc not in {"03", "07", "08"}:
            raise ValidationError(
                f"RC item {idx}: tipo_doc {item.tipo_doc!r} invalido "
                f"(validos: 03 boleta, 07 NC sobre boleta, 08 ND sobre boleta)"
            )
        if item.estado not in {"1", "2", "3"}:
            raise ValidationError(
                f"RC item {idx}: estado {item.estado!r} invalido "
                f"(validos: 1 adicionar, 2 modificar, 3 anular)"
            )

    template = _env.get_template("summary_RC.xml.j2")
    items = [_enrich_summary_item(it) for it in inv.items]
    rendered = template.render(inv=inv, items=items)
    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def _enrich_retention_item(item) -> dict:
    """Pre-formatea fechas y montos para la plantilla retention_20.

    Pre-cuantiza montos a 2 decimales (lo que SUNAT espera en el XML) y
    serializa las fechas a ISO; la plantilla queda libre de logica.
    """
    payload = {
        "tipo_doc": item.tipo_doc,
        "serie": item.serie,
        "numero": item.numero,
        "fecha_emision": item.fecha_emision.isoformat(),
        "moneda": item.moneda,
        "total": _q(item.total),
        "fecha_pago": item.fecha_pago.isoformat(),
        "importe_sin_retencion": _q(item.importe_sin_retencion),
        "importe_retencion": _q(item.importe_retencion),
        "fecha_retencion": item.fecha_retencion.isoformat(),
        "importe_neto_pagado": _q(item.importe_neto_pagado),
        "correlativo_pago": item.correlativo_pago,
        "tipo_cambio": _q(item.tipo_cambio) if item.tipo_cambio is not None else None,
        "tipo_cambio_fecha": (
            item.tipo_cambio_fecha.isoformat() if item.tipo_cambio_fecha else None
        ),
    }
    return payload


def build_retention_xml(inv: RetentionInput) -> str:
    """Renderiza un comprobante de retencion (tipo 20) UBL sin firmar.

    Estructura UBL especifica de SUNAT (namespace `sunat:Retention-1`,
    base UBL 2.0):
      * Sin LegalMonetaryTotal — el monto total retenido va directo en
        <cbc:TotalInvoiceAmount> del Retention.
      * <cac:AgentParty> = agente de retencion (RUC propio del emisor).
      * <cac:ReceiverParty> = proveedor retenido (puede ser RUC o DNI).
      * <sac:SUNATRetentionSystemCode> y <sac:SUNATRetentionPercent>:
        regimen y tasa.
      * <sac:SUNATRetentionDocumentReference> por cada pago retenido
        (puede haber varios contra la misma factura si hay pagos
        parciales).

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    validate_identity_doc(inv.receptor.tipo_doc, inv.receptor.numero_doc)
    validate_emission_date(inv.fecha_emision)
    validate_retention(inv)

    template = _env.get_template("retention_20.xml.j2")
    items = [_enrich_retention_item(it) for it in inv.items]
    rendered = template.render(
        inv=inv,
        items=items,
        tasa=_q(inv.tasa),
        total_retenido=_q(inv.total_retenido),
        total_pagado=_q(inv.total_pagado),
    )
    etree.fromstring(rendered.encode("utf-8"))
    return rendered


def _enrich_grline(line: GRLine) -> dict:
    return {
        "codigo": line.codigo,
        "descripcion": line.descripcion,
        "unidad": line.unidad,
        "cantidad": str(line.cantidad),
    }


def build_despatchadvice_xml(inv: DespatchAdviceInput) -> str:
    """Renderiza un DespatchAdvice UBL 2.1 (tipo 09) sin firmar.

    Diferencias UBL respecto a Invoice/CreditNote:
      * Root <DespatchAdvice> con namespace DespatchAdvice-2.
      * Sin valores monetarios: no TaxTotal, no LegalMonetaryTotal.
      * Datos de traslado en <cac:Shipment>: motivo, modalidad, peso, rutas.
      * Lineas en <cac:DespatchLine> con <cbc:DeliveredQuantity>.
      * Destinatario en <cac:DeliveryCustomerParty> (no AccountingCustomerParty).
      * Emisor/remitente en <cac:DespatchSupplierParty>.

    El elemento <ext:ExtensionContent/> queda vacio para que el signer
    inserte ahi la firma XMLDSig.
    """
    validate_emisor(inv.emisor)
    validate_identity_doc(inv.destinatario.tipo_doc, inv.destinatario.numero_doc)
    validate_emission_date(inv.fecha_emision)
    validate_lines(inv.lines)

    template = _env.get_template("despatchadvice_09.xml.j2")
    enriched_lines = [_enrich_grline(line) for line in inv.lines]

    rendered = template.render(
        inv=inv,
        lines=enriched_lines,
        peso_bruto=_q(inv.peso_bruto_total),
    )

    etree.fromstring(rendered.encode("utf-8"))
    return rendered
