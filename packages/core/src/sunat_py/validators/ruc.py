from sunat_py.errors import ValidationError

_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def validate_ruc(ruc: str) -> None:
    """Valida formato y digito verificador de un RUC peruano.

    El RUC SUNAT tiene 11 digitos numericos. El digito 11 es el verificador
    calculado con modulo 11 sobre los primeros 10 digitos y los pesos
    fijos (5, 4, 3, 2, 7, 6, 5, 4, 3, 2). Si el resto es < 2 el DV es
    `11 - resto - 10` (es decir, 0 o 1); en cualquier otro caso el DV es
    `11 - resto`.

    El primer digito ademas determina la categoria del contribuyente:
    `10` persona natural, `15`/`17` no domiciliados, `20` persona juridica.
    SUNAT acepta `10`, `15`, `16`, `17` y `20` como prefijos validos.
    """
    if not isinstance(ruc, str):
        raise ValidationError(f"RUC debe ser str, recibido {type(ruc).__name__}")
    if len(ruc) != 11:
        raise ValidationError(f"RUC debe tener 11 digitos, tiene {len(ruc)}: {ruc!r}")
    if not ruc.isdigit():
        raise ValidationError(f"RUC debe ser numerico: {ruc!r}")

    prefijo = ruc[:2]
    if prefijo not in {"10", "15", "16", "17", "20"}:
        raise ValidationError(
            f"prefijo de RUC invalido: {prefijo!r}. SUNAT acepta 10, 15, 16, 17, 20"
        )

    suma = sum(int(d) * w for d, w in zip(ruc[:10], _WEIGHTS, strict=True))
    resto = suma % 11
    dv_calculado = (11 - resto) % 11
    if dv_calculado == 10:
        dv_calculado = 0
    dv_recibido = int(ruc[10])
    if dv_calculado != dv_recibido:
        raise ValidationError(
            f"digito verificador invalido para RUC {ruc!r}: "
            f"esperado {dv_calculado}, recibido {dv_recibido}"
        )
