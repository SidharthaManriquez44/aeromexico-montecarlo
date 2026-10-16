import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from src.aeromexico_montecarlo.modelo import (  # noqa: E402
    ALTERNATIVAS,
    Supuestos,
    calcular_utilidades,
    generar_escenarios,
    punto_equilibrio,
    resumen_riesgo,
    validar_probabilidades,
)


def test_probabilidades_validas_y_rechazo_de_suma_incorrecta():
    validar_probabilidades((0.25, 0.5, 0.25))
    with pytest.raises(ValueError, match="sumar 1"):
        validar_probabilidades((0.2, 0.5, 0.2))


@pytest.mark.parametrize(
    "probabilidades", [(-0.1, 0.6, 0.5), (0.2, 0.8, 0.1), (float("nan"), 0.5, 0.5)]
)
def test_probabilidades_invalidas(probabilidades):
    with pytest.raises(ValueError):
        validar_probabilidades(probabilidades)


def test_simulacion_reproducible_y_tamano():
    s = Supuestos(iteraciones=500, semilla=7)
    a, b = generar_escenarios(s), generar_escenarios(s)
    assert len(a) == 500
    assert a.equals(b)


def test_utilidades_tienen_columnas_y_son_finitas():
    escenarios = generar_escenarios(Supuestos(iteraciones=200))
    utilidades = calcular_utilidades(escenarios)
    assert list(utilidades.columns) == [a.nombre for a in ALTERNATIVAS]
    assert np.isfinite(utilidades.to_numpy()).all()


def test_pasajeros_atendidos_nunca_superan_capacidad():
    escenarios = generar_escenarios(Supuestos(iteraciones=100))
    demanda = escenarios.demanda_pasajeros.to_numpy()
    for alternativa in ALTERNATIVAS:
        assert (
            np.minimum(demanda, alternativa.capacidad_anual_pasajeros).max()
            <= alternativa.capacidad_anual_pasajeros
        )


def test_resumen_riesgo_incluye_metricas_y_vme_consistente():
    escenarios = generar_escenarios(Supuestos(iteraciones=300))
    u = calcular_utilidades(escenarios)
    r = resumen_riesgo(u)
    assert {"VME_mxn", "probabilidad_perdida", "VaR_5_mxn", "CVaR_5_mxn"}.issubset(
        r.columns
    )
    assert np.isclose(
        r.set_index("alternativa").loc[u.columns[0], "VME_mxn"], u[u.columns[0]].mean()
    )
    assert r.probabilidad_perdida.between(0, 1).all()


def test_punto_equilibrio_y_restriccion_de_margen():
    r = punto_equilibrio()
    assert len(r) == 3
    assert (r.pasajeros_equilibrio > 0).all()
    with pytest.raises(ValueError, match="superar"):
        punto_equilibrio(tarifa_mxn=800, costo_variable_mxn=850)
