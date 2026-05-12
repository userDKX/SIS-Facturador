from fastapi import APIRouter, Depends, HTTPException, status
from requests import RequestException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sis_facturador.database import get_db
from sis_facturador.models.despatch_advice import DespatchAdvice
from sis_facturador.schemas.despatch_advice import DespatchAdviceCreate, DespatchAdviceResponse
from sis_facturador.services.despatch_advice_service import create_and_send_despatch_advice

router = APIRouter()


_POST_RESPONSES = {
    200: {
        "description": (
            "Guia de remision procesada. El campo `status` indica el resultado de SUNAT: "
            "`accepted` (code=0), `accepted_with_obs` (code=098) o `rejected`."
        ),
    },
    409: {
        "description": (
            "Ya existe una guia de remision con esa combinacion de `(ruc_emisor, serie, numero)`."
        ),
    },
    422: {
        "description": (
            "Payload invalido. Causas tipicas: la `serie` no comienza con T, "
            "o falta `transportista` para modalidad '01', o falta `conductor`/`vehiculo` "
            "para modalidad '02'."
        ),
    },
    502: {
        "description": (
            "SUNAT GRE no respondio correctamente: error HTTP, OAuth2 fallido o "
            "timeout del polling de CDR."
        ),
    },
}


@router.post(
    "",
    response_model=DespatchAdviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Emitir guia de remision",
    description=(
        "Construye el UBL 2.1 `<DespatchAdvice>`, lo firma, lo empaqueta en ZIP y lo "
        "envia a SUNAT por la Nueva GRE REST (api-cpe.sunat.gob.pe). Persiste la GR "
        "con el resultado y devuelve el registro completo con URLs al XML firmado "
        "y al CDR.\n\n"
        "**Idempotencia**: la combinacion `(ruc, serie, numero)` es UNIQUE. "
        "Reintentos con el mismo payload devuelven 409.\n\n"
        "**Modalidad**: '01' transporte publico requiere `transportista`; "
        "'02' transporte privado requiere `conductor` y `vehiculo`."
    ),
    responses=_POST_RESPONSES,
)
def post_despatch_advice(
    payload: DespatchAdviceCreate, db: Session = Depends(get_db)
) -> DespatchAdvice:
    try:
        return create_and_send_despatch_advice(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe una guia de remision con serie={payload.serie} numero={payload.numero}"
            ),
        ) from exc
    except RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT GRE no respondio correctamente: {exc}",
        ) from exc


@router.get(
    "/{despatch_advice_id}",
    response_model=DespatchAdviceResponse,
    summary="Consultar guia de remision por ID",
    description=(
        "Devuelve la guia de remision persistida. **No** consulta a SUNAT — es "
        "read-only contra la BD local."
    ),
    responses={
        404: {"description": "No existe guia de remision con ese ID."},
    },
)
def get_despatch_advice(despatch_advice_id: int, db: Session = Depends(get_db)) -> DespatchAdvice:
    gr = db.get(DespatchAdvice, despatch_advice_id)
    if gr is None:
        raise HTTPException(status_code=404, detail="Guia de remision no encontrada")
    return gr
