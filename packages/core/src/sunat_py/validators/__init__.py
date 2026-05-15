"""Validaciones previas al armado del XML.

Las funciones de este modulo no devuelven nada cuando el input es valido y
lanzan `sunat_py.errors.ValidationError` con un mensaje claro cuando
algo esta mal. Se invocan automaticamente desde los builders, pero tambien
sirven standalone (validar un RUC antes de aceptarlo en un form, por
ejemplo).
"""

from sunat_py.validators.dates import LIMA_TZ, today_lima, validate_emission_date
from sunat_py.validators.emisor import validate_emisor
from sunat_py.validators.identity_doc import validate_identity_doc
from sunat_py.validators.perception import validate_perception
from sunat_py.validators.retention import validate_retention
from sunat_py.validators.ruc import validate_ruc
from sunat_py.validators.totals import validate_lines

__all__ = [
    "LIMA_TZ",
    "today_lima",
    "validate_emisor",
    "validate_emission_date",
    "validate_identity_doc",
    "validate_lines",
    "validate_perception",
    "validate_retention",
    "validate_ruc",
]
