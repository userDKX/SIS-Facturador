from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree

from pe_invoicing.ubl.models import (
    CreditNoteInput,
    InvoiceInput,
    InvoiceLine,
    InvoiceTotals,
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
