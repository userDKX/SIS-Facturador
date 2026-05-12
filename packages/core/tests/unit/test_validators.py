from datetime import timedelta
from decimal import Decimal

import pytest
from sunat_py import (
    GRLine,
    InvoiceLine,
    ValidationError,
    today_lima,
    validate_emission_date,
    validate_identity_doc,
    validate_lines,
    validate_ruc,
)


# ---------------------------------------------------------------------------
# validate_ruc
# ---------------------------------------------------------------------------


class TestValidateRuc:
    def test_ruc_moddatos_es_valido(self):
        validate_ruc("20000000001")

    def test_ruc_real_con_dv_cero_es_valido(self):
        # 20100070970: el algoritmo da resto=1 -> DV calculado=10 -> normaliza a 0.
        validate_ruc("20100070970")

    def test_ruc_persona_natural_prefijo_10(self):
        # 10000000006: prefijo 10 valido. Verificado manualmente con el algoritmo
        # (suma=5, resto=5, DV=11-5=6).
        validate_ruc("10000000006")

    def test_ruc_con_dv_incorrecto_falla(self):
        with pytest.raises(ValidationError, match="digito verificador"):
            validate_ruc("20000000002")

    def test_ruc_con_longitud_incorrecta_falla(self):
        with pytest.raises(ValidationError, match="11 digitos"):
            validate_ruc("2000000001")

    def test_ruc_con_caracteres_no_numericos_falla(self):
        with pytest.raises(ValidationError, match="numerico"):
            validate_ruc("2000000000A")

    def test_ruc_con_prefijo_invalido_falla(self):
        with pytest.raises(ValidationError, match="prefijo"):
            validate_ruc("12345678901")

    def test_ruc_no_string_falla(self):
        with pytest.raises(ValidationError, match="str"):
            validate_ruc(20000000001)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_identity_doc
# ---------------------------------------------------------------------------


class TestValidateIdentityDoc:
    def test_ruc_valido_via_router(self):
        validate_identity_doc("6", "20000000001")

    def test_ruc_invalido_via_router_falla(self):
        with pytest.raises(ValidationError):
            validate_identity_doc("6", "20000000002")

    def test_dni_valido(self):
        validate_identity_doc("1", "12345678")

    def test_dni_corto_falla(self):
        with pytest.raises(ValidationError, match="DNI"):
            validate_identity_doc("1", "1234567")

    def test_dni_no_numerico_falla(self):
        with pytest.raises(ValidationError, match="DNI"):
            validate_identity_doc("1", "1234567A")

    def test_ce_valido(self):
        validate_identity_doc("4", "ABC123456")

    def test_ce_muy_corto_falla(self):
        with pytest.raises(ValidationError, match="carnet de extranjeria"):
            validate_identity_doc("4", "ABC12")

    def test_pasaporte_libre(self):
        validate_identity_doc("7", "P12345")

    def test_sin_documento_no_vacio(self):
        validate_identity_doc("0", "-")

    def test_tipo_invalido_falla(self):
        with pytest.raises(ValidationError, match="catalogo SUNAT 06"):
            validate_identity_doc("9", "12345678")


# ---------------------------------------------------------------------------
# validate_emission_date
# ---------------------------------------------------------------------------


class TestValidateEmissionDate:
    def test_hoy_es_valido(self):
        validate_emission_date(today_lima())

    def test_ayer_es_valido(self):
        validate_emission_date(today_lima() - timedelta(days=1))

    def test_siete_dias_atras_es_valido(self):
        validate_emission_date(today_lima() - timedelta(days=7))

    def test_ocho_dias_atras_falla(self):
        with pytest.raises(ValidationError, match="dias de atraso"):
            validate_emission_date(today_lima() - timedelta(days=8))

    def test_fecha_futura_falla(self):
        with pytest.raises(ValidationError, match="futura"):
            validate_emission_date(today_lima() + timedelta(days=1))

    def test_no_es_date_falla(self):
        with pytest.raises(ValidationError, match="date"):
            validate_emission_date("2026-05-11")  # type: ignore[arg-type]

    def test_backdate_extendido_por_parametro(self):
        # Para casos de contingencia el llamador puede ampliar el limite.
        validate_emission_date(
            today_lima() - timedelta(days=30), max_backdate_days=60
        )


# ---------------------------------------------------------------------------
# validate_lines
# ---------------------------------------------------------------------------


class TestValidateLines:
    def _line(self, **overrides) -> InvoiceLine:
        defaults = dict(
            codigo="P001",
            descripcion="PRODUCTO",
            unidad="NIU",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100"),
            igv_afectacion="10",
        )
        defaults.update(overrides)
        return InvoiceLine(**defaults)

    def test_lines_vacio_falla(self):
        with pytest.raises(ValidationError, match="vacio"):
            validate_lines([])

    def test_linea_valida_pasa(self):
        validate_lines([self._line()])

    def test_cantidad_cero_falla(self):
        with pytest.raises(ValidationError, match="cantidad"):
            validate_lines([self._line(cantidad=Decimal("0"))])

    def test_cantidad_negativa_falla(self):
        with pytest.raises(ValidationError, match="cantidad"):
            validate_lines([self._line(cantidad=Decimal("-1"))])

    def test_codigo_vacio_falla(self):
        with pytest.raises(ValidationError, match="codigo"):
            validate_lines([self._line(codigo="")])

    def test_descripcion_vacia_falla(self):
        with pytest.raises(ValidationError, match="descripcion"):
            validate_lines([self._line(descripcion="")])

    def test_precio_negativo_falla(self):
        with pytest.raises(ValidationError, match="precio_unitario"):
            validate_lines([self._line(precio_unitario=Decimal("-1"))])

    def test_precio_cero_es_valido(self):
        # Gratuitas tienen precio 0; el SDK no debe rechazarlo a priori.
        validate_lines([self._line(precio_unitario=Decimal("0"))])

    def test_igv_afectacion_invalida_falla(self):
        with pytest.raises(ValidationError, match="igv_afectacion"):
            validate_lines([self._line(igv_afectacion="99")])

    def test_grline_no_valida_precio(self):
        gr = GRLine(
            codigo="P001",
            descripcion="PRODUCTO",
            unidad="NIU",
            cantidad=Decimal("5"),
        )
        validate_lines([gr])

    def test_segunda_linea_invalida_reporta_indice(self):
        good = self._line()
        bad = self._line(cantidad=Decimal("0"))
        with pytest.raises(ValidationError, match="linea 2"):
            validate_lines([good, bad])
