"""Modelo académico de decisión de capacidad para una ruta hipotética.

Todas las cifras son supuestos didácticos en MXN y corresponden a un año.
No representan datos internos ni resultados oficiales de Grupo Aeroméxico.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Alternativa:
    nombre: str
    descripcion: str
    capacidad_anual_pasajeros: int
    litros_combustible_por_asiento_ofertado: float
    costo_fijo_anual_mxn: float


@dataclass(frozen=True)
class Supuestos:
    iteraciones: int = 10_000
    semilla: int = 42
    probabilidades_demanda: tuple[float, float, float] = (0.25, 0.50, 0.25)
    tarifa_baja_mxn: tuple[float, float] = (3_500.0, 4_300.0)
    tarifa_media_mxn: tuple[float, float] = (4_000.0, 5_000.0)
    tarifa_alta_mxn: tuple[float, float] = (4_500.0, 5_600.0)
    costo_variable_pasajero_mxn: tuple[float, float, float] = (650.0, 850.0, 1_100.0)
    precio_combustible_mxn_litro: tuple[float, float, float] = (17.0, 23.0, 34.0)


ALTERNATIVAS: tuple[Alternativa, ...] = (
    Alternativa(
        "A. Mantener capacidad",
        "Operación actual de referencia",
        100_000,
        35.0,
        125_000_000,
    ),
    Alternativa(
        "B. Aumentar frecuencias",
        "Más vuelos con aeronaves de referencia",
        125_000,
        34.0,
        157_000_000,
    ),
    Alternativa(
        "C. Cambiar aeronave",
        "Aeronave de mayor capacidad y menor consumo por asiento",
        115_000,
        30.0,
        145_000_000,
    ),
)


def validar_probabilidades(
    probabilidades: tuple[float, ...] | list[float], tolerancia: float = 1e-9
) -> None:
    """Válida un vector de probabilidades exhaustivo y mutuamente excluyente."""
    p = np.asarray(probabilidades, dtype=float)
    if p.ndim != 1 or p.size == 0:
        raise ValueError("Las probabilidades deben formar un vector no vacío.")
    if not np.all(np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("Cada probabilidad debe ser finita y estar entre 0 y 1.")
    if not np.isclose(p.sum(), 1.0, atol=tolerancia, rtol=0):
        raise ValueError(
            f"Las probabilidades deben sumar 1; suma recibida: {p.sum():.8f}."
        )


def validar_supuestos(s: Supuestos) -> None:
    if s.iteraciones <= 0:
        raise ValueError("El número de iteraciones debe ser positivo.")
    if s.semilla < 0:
        raise ValueError("La semilla debe ser un entero no negativo.")
    validar_probabilidades(s.probabilidades_demanda)
    for nombre, rango in (
        ("tarifa baja", s.tarifa_baja_mxn),
        ("tarifa media", s.tarifa_media_mxn),
        ("tarifa alta", s.tarifa_alta_mxn),
    ):
        if len(rango) != 2 or rango[0] <= 0 or rango[1] < rango[0]:
            raise ValueError(f"Rango inválido para {nombre}.")
    for nombre, valores in (
        ("costo variable", s.costo_variable_pasajero_mxn),
        ("combustible", s.precio_combustible_mxn_litro),
    ):
        if len(valores) != 3 or not (0 < valores[0] <= valores[1] <= valores[2]):
            raise ValueError(f"Se esperan mínimo, moda y máximo válidos para {nombre}.")


def generar_escenarios(s: Supuestos) -> pd.DataFrame:
    """Genera escenarios comunes a las alternativas para comparar con menos ruido."""
    validar_supuestos(s)
    rng = np.random.default_rng(s.semilla)
    n = s.iteraciones
    nivel = rng.choice(3, size=n, p=s.probabilidades_demanda)

    # La demanda anual se modela como triangular dentro de cada régimen.
    parametros_demanda = (
        (65_000.0, 82_000.0, 100_000.0),
        (82_000.0, 105_000.0, 130_000.0),
        (105_000.0, 132_000.0, 160_000.0),
    )
    demanda = np.empty(n)
    tarifa = np.empty(n)
    rangos_tarifa = (s.tarifa_baja_mxn, s.tarifa_media_mxn, s.tarifa_alta_mxn)
    for i in range(3):
        mascara = nivel == i
        bajo, moda, alto = parametros_demanda[i]
        demanda[mascara] = rng.triangular(bajo, moda, alto, mascara.sum())
        tmin, tmax = rangos_tarifa[i]
        tarifa[mascara] = rng.uniform(tmin, tmax, mascara.sum())

    costo_variable = rng.triangular(*s.costo_variable_pasajero_mxn, size=n)
    precio_combustible = rng.triangular(*s.precio_combustible_mxn_litro, size=n)
    return pd.DataFrame(
        {
            "regimen_demanda": np.array(["baja", "media", "alta"])[nivel],
            "demanda_pasajeros": demanda,
            "tarifa_mxn": tarifa,
            "costo_variable_pasajero_mxn": costo_variable,
            "precio_combustible_mxn_litro": precio_combustible,
        }
    )


def calcular_utilidades(
    escenarios: pd.DataFrame,
    alternativas: tuple[Alternativa, ...] = ALTERNATIVAS,
    multiplicador_demanda: float = 1.0,
    multiplicador_tarifa: float = 1.0,
    multiplicador_combustible: float = 1.0,
) -> pd.DataFrame:
    """Calcula utilidad anual por iteración y alternativa.

    Utilidad = pasajeros atendidos × (tarifa − costo variable)
                                    − combustible − costo fijo.
    El combustible se asocia a la capacidad anual ofrecida y no a la ocupación.
    """
    if min(multiplicador_demanda, multiplicador_tarifa, multiplicador_combustible) <= 0:
        raise ValueError("Los multiplicadores de sensibilidad deben ser positivos.")
    demanda = escenarios["demanda_pasajeros"].to_numpy() * multiplicador_demanda
    tarifa = escenarios["tarifa_mxn"].to_numpy() * multiplicador_tarifa
    variable = escenarios["costo_variable_pasajero_mxn"].to_numpy()
    precio = (
        escenarios["precio_combustible_mxn_litro"].to_numpy()
        * multiplicador_combustible
    )
    resultado: dict[str, np.ndarray] = {}
    for alt in alternativas:
        atendidos = np.minimum(demanda, alt.capacidad_anual_pasajeros)
        combustible = (
            alt.capacidad_anual_pasajeros
            * alt.litros_combustible_por_asiento_ofertado
            * precio
        )
        resultado[alt.nombre] = (
            atendidos * (tarifa - variable) - combustible - alt.costo_fijo_anual_mxn
        )
    return pd.DataFrame(resultado)


def resumen_riesgo(utilidades: pd.DataFrame) -> pd.DataFrame:
    """VME y métricas de riesgo, con VaR y CVaR en la cola inferior del 5 %."""
    filas = []
    for nombre in utilidades.columns:
        x = utilidades[nombre].to_numpy()
        var_5 = float(np.quantile(x, 0.05))
        filas.append(
            {
                "alternativa": nombre,
                "VME_mxn": float(np.mean(x)),
                "mediana_mxn": float(np.median(x)),
                "desviacion_estandar_mxn": float(np.std(x, ddof=1)),
                "probabilidad_perdida": float(np.mean(x < 0)),
                "VaR_5_mxn": var_5,
                "CVaR_5_mxn": float(np.mean(x[x <= var_5])),
            }
        )
    return (
        pd.DataFrame(filas)
        .sort_values("VME_mxn", ascending=False)
        .reset_index(drop=True)
    )


def punto_equilibrio(
    alternativas: tuple[Alternativa, ...] = ALTERNATIVAS,
    tarifa_mxn: float = 4_600.0,
    costo_variable_mxn: float = 850.0,
    precio_combustible_mxn_litro: float = 25.0,
) -> pd.DataFrame:
    """Pasajeros necesarios para utilidad cero bajo valores de referencia."""
    if tarifa_mxn <= costo_variable_mxn:
        raise ValueError("La tarifa debe superar el costo variable por pasajero.")
    if min(tarifa_mxn, costo_variable_mxn, precio_combustible_mxn_litro) < 0:
        raise ValueError("Los valores de referencia no pueden ser negativos.")
    filas = []
    for alt in alternativas:
        costo_fijo_total = (
            alt.costo_fijo_anual_mxn
            + alt.capacidad_anual_pasajeros
            * alt.litros_combustible_por_asiento_ofertado
            * precio_combustible_mxn_litro
        )
        pasajeros = costo_fijo_total / (tarifa_mxn - costo_variable_mxn)
        filas.append(
            {
                "alternativa": alt.nombre,
                "pasajeros_equilibrio": pasajeros,
                "capacidad_anual_pasajeros": alt.capacidad_anual_pasajeros,
                "equilibrio_factible": pasajeros <= alt.capacidad_anual_pasajeros,
                "utilizacion_equilibrio": pasajeros / alt.capacidad_anual_pasajeros,
                "tarifa_referencia_mxn": tarifa_mxn,
                "costo_variable_referencia_mxn": costo_variable_mxn,
                "combustible_referencia_mxn_litro": precio_combustible_mxn_litro,
            }
        )
    return pd.DataFrame(filas)


def analisis_sensibilidad(
    escenarios: pd.DataFrame, alternativas: tuple[Alternativa, ...] = ALTERNATIVAS
) -> pd.DataFrame:
    """VME ante shocks de una variable, usando los mismos escenarios aleatorios."""
    perturbaciones: Mapping[str, tuple[str, float]] = {
        "Demanda -20 %": ("demanda", 0.80),
        "Demanda -10 %": ("demanda", 0.90),
        "Base": ("base", 1.0),
        "Demanda +10 %": ("demanda", 1.10),
        "Demanda +20 %": ("demanda", 1.20),
        "Tarifa -20 %": ("tarifa", 0.80),
        "Tarifa -10 %": ("tarifa", 0.90),
        "Tarifa +10 %": ("tarifa", 1.10),
        "Tarifa +20 %": ("tarifa", 1.20),
        "Combustible -20 %": ("combustible", 0.80),
        "Combustible -10 %": ("combustible", 0.90),
        "Combustible +10 %": ("combustible", 1.10),
        "Combustible +20 %": ("combustible", 1.20),
    }
    filas = []
    for etiqueta, (variable, factor) in perturbaciones.items():
        kwargs = {
            "multiplicador_demanda": 1.0,
            "multiplicador_tarifa": 1.0,
            "multiplicador_combustible": 1.0,
        }
        if variable == "demanda":
            kwargs["multiplicador_demanda"] = factor
        elif variable == "tarifa":
            kwargs["multiplicador_tarifa"] = factor
        elif variable == "combustible":
            kwargs["multiplicador_combustible"] = factor
        u = calcular_utilidades(escenarios, alternativas, **kwargs)
        for alt in u.columns:
            filas.append(
                {
                    "escenario": etiqueta,
                    "alternativa": alt,
                    "VME_mxn": float(u[alt].mean()),
                }
            )
    return pd.DataFrame(filas)
