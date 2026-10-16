from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from aeromexico_montecarlo.modelo import (
    ALTERNATIVAS,
    Supuestos,
    analisis_sensibilidad,
    calcular_utilidades,
    generar_escenarios,
    punto_equilibrio,
    resumen_riesgo,
)


def ejecutar(directorio_salida: Path) -> None:
    directorio_salida.mkdir(parents=True, exist_ok=True)
    supuestos = Supuestos()
    escenarios = generar_escenarios(supuestos)
    utilidades = calcular_utilidades(escenarios)
    resumen = resumen_riesgo(utilidades)
    equilibrio = punto_equilibrio()
    sensibilidad = analisis_sensibilidad(escenarios)

    escenarios.to_csv(
        directorio_salida / "escenarios_simulados.csv",
        index=False,
        encoding="utf-8-sig",
    )
    utilidades.to_csv(
        directorio_salida / "utilidades_por_iteracion.csv",
        index=False,
        encoding="utf-8-sig",
    )
    resumen.to_csv(
        directorio_salida / "resumen_resultados.csv", index=False, encoding="utf-8-sig"
    )
    equilibrio.to_csv(
        directorio_salida / "punto_equilibrio.csv", index=False, encoding="utf-8-sig"
    )
    sensibilidad.to_csv(
        directorio_salida / "sensibilidad.csv", index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    for alt in utilidades.columns:
        ax.hist(utilidades[alt] / 1e6, bins=55, alpha=0.45, label=alt)
    ax.axvline(0, color="black", linewidth=1, linestyle="--")
    ax.set(
        title="Distribución de utilidad anual simulada",
        xlabel="Utilidad anual (millones de MXN)",
        ylabel="Frecuencia",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(directorio_salida / "distribucion_utilidades.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    graf = resumen.sort_values("VME_mxn")
    ax.barh(
        graf["alternativa"],
        graf["VME_mxn"] / 1e6,
        color=["#4472C4", "#70AD47", "#ED7D31"],
    )
    ax.set(
        title="Valor monetario esperado por alternativa",
        xlabel="VME anual (millones de MXN)",
    )
    ax.axvline(0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(directorio_salida / "vme_alternativas.png", dpi=160)
    plt.close(fig)

    base = sensibilidad[sensibilidad.escenario == "Base"].set_index("alternativa")[
        "VME_mxn"
    ]
    fig, axes = plt.subplots(1, len(ALTERNATIVAS), figsize=(14, 6), sharey=True)
    for ax, alt in zip(
        axes,
        [a.nombre for a in ALTERNATIVAS],
        strict=True,
    ):
        sub = sensibilidad[sensibilidad.alternativa == alt].copy()
        sub["cambio_pct"] = (sub["VME_mxn"] - base[alt]) / 1e6
        sub = sub[sub.escenario != "Base"].sort_values("cambio_pct")
        ax.barh(
            sub["escenario"],
            sub["cambio_pct"],
            color=["#C0504D" if v < 0 else "#70AD47" for v in sub["cambio_pct"]],
        )
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(alt.split(". ", 1)[0])
        ax.set_xlabel("Cambio del VME (millones MXN)")
    axes[0].set_ylabel("Shock respecto al caso base")
    fig.suptitle("Sensibilidad del VME a cambios de demanda, tarifa y combustible")
    fig.tight_layout()
    fig.savefig(directorio_salida / "sensibilidad_vme.png", dpi=160)
    plt.close(fig)

    print(f"Iteraciones: {supuestos.iteraciones:,} | Semilla: {supuestos.semilla}")
    print("VME y riesgo (MXN anuales):")
    print(
        resumen.to_string(
            index=False,
            formatters={
                c: (lambda x: f"{x:,.0f}")
                for c in [
                    "VME_mxn",
                    "mediana_mxn",
                    "desviacion_estandar_mxn",
                    "VaR_5_mxn",
                    "CVaR_5_mxn",
                ]
            }
            | {"probabilidad_perdida": lambda x: f"{x:.1%}"},
        )
    )
    print("\nPunto de equilibrio (supuestos de referencia):")
    print(
        equilibrio[
            [
                "alternativa",
                "pasajeros_equilibrio",
                "capacidad_anual_pasajeros",
                "equilibrio_factible",
            ]
        ].to_string(
            index=False, formatters={"pasajeros_equilibrio": lambda x: f"{x:,.0f}"}
        )
    )
    print(f"\nArchivos guardados en: {directorio_salida.resolve()}")


if __name__ == "__main__":
    ejecutar(Path(__file__).resolve().parents[1] / "results")
