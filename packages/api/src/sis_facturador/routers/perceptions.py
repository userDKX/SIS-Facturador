from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sunat_py import SunatError

from sis_facturador.database import get_db
from sis_facturador.models.perception import Perception
from sis_facturador.schemas.perception import PerceptionCreate, PerceptionResponse
from sis_facturador.services.perception_service import create_and_send_perception

router = APIRouter()


_POST_RESPONSES = {
    200: {
        "description": (
            "Comprobante de percepción procesado. El campo `status` indica el "
            "resultado de SUNAT: `accepted` (CDR code=0), `accepted_with_obs` "
            "(code=098) o `rejected`."
        ),
    },
    409: {
        "description": (
            "Ya existe un comprobante de percepción con esa combinación de "
            "`(ruc_emisor, serie, numero)`. Unicidad garantizada por constraint."
        ),
    },
    422: {
        "description": (
            "Payload inválido. Causas típicas: serie que no empieza con `P`, "
            "sumas que no cuadran, o `importe_total_cobrado != "
            "importe_sin_percepcion + importe_percepcion`."
        ),
    },
    502: {
        "description": (
            "SUNAT no respondió correctamente. Si el RUC no es agente de "
            "percepción, SUNAT devuelve código 1071."
        ),
    },
}


@router.post(
    "",
    response_model=PerceptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Emitir comprobante de percepción",
    description=(
        "Construye el UBL `<Perception>` (UBL 2.0 + extensiones SUNAT), lo "
        "firma, lo empaqueta en ZIP y lo envía a SUNAT vía sendBill. Persiste "
        "el comprobante con sus items y devuelve el registro completo.\n\n"
        "**Solo agentes de percepción**: SUNAT rechaza con código 1071 si el "
        "RUC del emisor no está en el padrón "
        "(<http://www.sunat.gob.pe/padronesnotificaciones/>).\n\n"
        "**Régimen** (catálogo SUNAT 22):\n"
        "  * `01` — Adquisición de combustible (tasa 1%)\n"
        "  * `02` — Venta interna (tasa 2%, régimen general)\n"
        "  * `03` — Importación de bienes\n\n"
        "**Aritmética**: a diferencia de retención, percepción SUMA — el "
        "`importe_total_cobrado` es lo que el agente cobró al cliente "
        "(importe original + percepción)."
    ),
    responses=_POST_RESPONSES,
)
def post_perception(
    payload: PerceptionCreate, db: Session = Depends(get_db)
) -> Perception:
    try:
        return create_and_send_perception(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe una percepcion con serie={payload.serie} "
                f"numero={payload.numero}"
            ),
        ) from exc
    except SunatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT no respondio correctamente: {exc.message}",
        ) from exc


@router.get(
    "/{perception_id}",
    response_model=PerceptionResponse,
    summary="Consultar comprobante de percepción por ID",
    description="Devuelve la percepción persistida con todos sus items.",
    responses={
        404: {"description": "No existe percepción con ese ID."},
    },
)
def get_perception(perception_id: int, db: Session = Depends(get_db)) -> Perception:
    per = db.get(Perception, perception_id)
    if per is None:
        raise HTTPException(status_code=404, detail="Percepcion no encontrada")
    return per
