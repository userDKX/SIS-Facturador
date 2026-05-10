"""pe-invoicing — SDK Python para SUNAT Peru.

Atajos para los simbolos mas usados. Si necesitas mas, los modulos
internos viven en `pe_invoicing.{ubl,signer,sunat,security}`.
"""

from pe_invoicing.security.cert_loader import (
    CertBundle,
    load_cert_from_base64,
    load_cert_from_pfx,
)
from pe_invoicing.signer.xmldsig import sign_invoice_xml
from pe_invoicing.sunat.client import (
    SunatError,
    SunatMode,
    SunatResult,
    SunatStatus,
    build_zeep_client,
    send_bill,
)
from pe_invoicing.sunat.packager import pack_invoice, unpack_cdr
from pe_invoicing.ubl.builder import (
    build_creditnote_xml,
    build_invoice_xml,
    compute_totals,
    monto_en_letras,
)
from pe_invoicing.ubl.models import (
    CreditNoteInput,
    InvoiceInput,
    InvoiceLine,
    InvoiceTotals,
    Party,
    ReferenciaDoc,
)

__version__ = "0.2.0"

__all__ = [
    "CertBundle",
    "CreditNoteInput",
    "InvoiceInput",
    "InvoiceLine",
    "InvoiceTotals",
    "Party",
    "ReferenciaDoc",
    "SunatError",
    "SunatMode",
    "SunatResult",
    "SunatStatus",
    "__version__",
    "build_creditnote_xml",
    "build_invoice_xml",
    "build_zeep_client",
    "compute_totals",
    "load_cert_from_base64",
    "load_cert_from_pfx",
    "monto_en_letras",
    "pack_invoice",
    "send_bill",
    "sign_invoice_xml",
    "unpack_cdr",
]
