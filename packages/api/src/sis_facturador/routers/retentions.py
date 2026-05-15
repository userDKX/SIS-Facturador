from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sunat_py import SunatError

from sis_facturador.database import get_db
from sis_facturador.models.retention import Retention
from sis_facturador.schemas.retention import RetentionCreate, RetentionResponse
from sis_facturador.services.retention_service import create_and_send_retention

router = APIRouter()


_POST_RESPONSES = {
    200: {
        "description": (
            "Comprobante de retención procesado. El campo `status` indica el "
            "resultado de SUNAT: `accepted` (CDR code=0), `accepted_with_obs` "
            "(code=098) o `rejected`."
        ),
    },
    409: {
        "description": (
            "Ya existe un comprobante de retención con esa combinación de "
            "`(ruc_emisor, serie, numero)`. Unicidad garantizada por constraint."
        ),
    },
    422: {
        "description": (
            "Payload inválido. Causas típicas: serie que no empieza con `R`, "
            "sumas de items que no cuadran con `total_retenido`/`total_pagado`, "
            "o `ref_moneda != PEN` sin `tipo_cambio`."
        ),
    },
    502: {
        "description": (
            "SUNAT no respondió correctamente: transporte, fault no parseable, "
            "credenciales inválidas, o el RUC no es agente de retención (código "
            "1071)."
        ),
    },
}


@router.post(
    "",
    response_model=RetentionResponse,
    status_code=status.HTTP_200_OK,
    summary="Emitir comprobante de retención",
    description=(
        "Construye el UBL `<Retention>` (UBL 2.0 + extensiones SUNAT), lo firma, "
        "lo empaqueta en ZIP y lo envía a SUNAT vía sendBill. Persiste el "
        "comprobante con sus items y devuelve el registro completo con URLs al "
        "XML firmado y al CDR.\n\n"
        "**Solo agentes de retención**: SUNAT rechaza con código 1071 si el RUC "
        "del emisor no está en el padrón de agentes "
        "(<http://www.sunat.gob.pe/padronesnotificaciones/>).\n\n"
        "**Idempotencia**: la combinación `(ruc, serie, numero)` es UNIQUE. "
        "Reintentos con el mismo payload devuelven 409.\n\n"
        "**Tasa**: 3.00 desde 01/03/2014; 6.00 solo si necesita emitir un "
        "comprobante histórico."
    ),
    responses=_POST_RESPONSES,
)
def post_retention(
    payload: RetentionCreate, db: Session = Depends(get_db)
) -> Retention:
    try:
        return create_and_send_retention(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe una retencion con serie={payload.serie} numero={payload.numero}"
            ),
        ) from exc
    except SunatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT no respondio correctamente: {exc.message}",
        ) from exc


@router.get(
    "/{retention_id}",
    response_model=RetentionResponse,
    summary="Consultar comprobante de retención por ID",
    description=(
        "Devuelve la retención persistida con todos sus items. **No** consulta "
        "a SUNAT — es read-only contra la BD local."
    ),
    responses={
        404: {"description": "No existe retención con ese ID."},
    },
)
def get_retention(retention_id: int, db: Session = Depends(get_db)) -> Retention:
    ret = db.get(Retention, retention_id)
    if ret is None:
        raise HTTPException(status_code=404, detail="Retencion no encontrada")
    return ret
