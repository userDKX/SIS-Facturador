"""Catalogos SUNAT embebidos como tipos Literal.

Cada modulo expone:
  * Un alias `Literal[...]` para usar en anotaciones de modelos (el IDE
    autocompleta los codigos validos al instanciar el dataclass).
  * Un dict `LABELS` que mapea cada codigo a su descripcion oficial SUNAT
    para mostrar en UI o logs.
  * Los codigos individuales como constantes (`FACTURA = "01"`, etc.)
    para uso ergonomico cuando no querras escribir el string literal.

Los catalogos cubiertos hoy son los que el SDK usa en builders y
validators. Si tu codigo necesita un catalogo que no esta aqui, podes
seguir usando `str` plano y agregarlo via PR — el SDK no se opone.
"""

from sunat_py.catalogs.credit_reason import (
    CREDIT_REASON_LABELS,
    CreditReasonCode,
)
from sunat_py.catalogs.debit_reason import (
    DEBIT_REASON_LABELS,
    DebitReasonCode,
)
from sunat_py.catalogs.document_types import (
    DOCUMENT_TYPE_LABELS,
    DocumentTypeCode,
)
from sunat_py.catalogs.identity_doc import (
    IDENTITY_DOC_LABELS,
    IdentityDocCode,
)
from sunat_py.catalogs.igv_affectation import (
    IGV_AFFECTATION_LABELS,
    IgvAffectationCode,
)
from sunat_py.catalogs.transport_modality import (
    TRANSPORT_MODALITY_LABELS,
    TransportModalityCode,
)
from sunat_py.catalogs.transport_reason import (
    TRANSPORT_REASON_LABELS,
    TransportReasonCode,
)

__all__ = [
    "CREDIT_REASON_LABELS",
    "CreditReasonCode",
    "DEBIT_REASON_LABELS",
    "DebitReasonCode",
    "DOCUMENT_TYPE_LABELS",
    "DocumentTypeCode",
    "IDENTITY_DOC_LABELS",
    "IdentityDocCode",
    "IGV_AFFECTATION_LABELS",
    "IgvAffectationCode",
    "TRANSPORT_MODALITY_LABELS",
    "TransportModalityCode",
    "TRANSPORT_REASON_LABELS",
    "TransportReasonCode",
]
