from datetime import date, datetime, timedelta, timezone

from sunat_py.errors import ValidationError

LIMA_TZ = timezone(timedelta(hours=-5))
_MAX_BACKDATE_DAYS = 7


def today_lima() -> date:
    """Devuelve la fecha actual segun el reloj de Lima (UTC-5, sin DST).

    SUNAT valida `fecha_emision` contra este reloj — no contra el del proceso.
    Usar este helper en lugar de `date.today()` para que el codigo se
    comporte igual corriendo local o en CI (que suele estar en UTC).
    """
    return datetime.now(LIMA_TZ).date()


def validate_emission_date(fecha: date, *, max_backdate_days: int = _MAX_BACKDATE_DAYS) -> None:
    """Valida que la fecha de emision sea utilizable contra SUNAT.

    Reglas:
      * No puede ser futura segun el reloj de Lima (UTC-5). SUNAT rechaza
        con error 2329 si la fecha es posterior al dia actual SUNAT.
      * No puede tener mas de `max_backdate_days` dias de atraso. SUNAT
        tiene plazos distintos por tipo de comprobante (boleta: el mismo
        dia o resumen, factura: hasta el dia siguiente, etc.) pero como
        regla general, 7 dias cubre los casos sanos sin entrar en
        contingencia.
    """
    if not isinstance(fecha, date):
        raise ValidationError(
            f"fecha_emision debe ser date, recibido {type(fecha).__name__}"
        )

    hoy = today_lima()
    if fecha > hoy:
        raise ValidationError(
            f"fecha_emision {fecha.isoformat()} es futura "
            f"(hoy en Lima: {hoy.isoformat()})"
        )

    delta = (hoy - fecha).days
    if delta > max_backdate_days:
        raise ValidationError(
            f"fecha_emision {fecha.isoformat()} tiene {delta} dias de atraso "
            f"(maximo: {max_backdate_days}). Para casos de contingencia "
            f"pasa explicitamente max_backdate_days mayor."
        )
