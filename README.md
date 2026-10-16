# Decisión de capacidad en una ruta hipotética de Aeroméxico

Proyecto académico en Python para comparar tres alternativas de capacidad mediante simulación Monte Carlo. El horizonte es **un año para las tres alternativas**, con **10,000 iteraciones** y semilla fija (**42**) para reproducir los resultados.

> **Alcance:** todas las cifras operativas y financieras del modelo son supuestos hipotéticos con fines académicos. No son datos internos, pronósticos ni resultados oficiales de Grupo Aeroméxico. El ejemplo representa una ruta hipotética agregada a un año.

## Pregunta de decisión

¿Qué alternativa ofrece el mayor valor monetario esperado anual, considerando la incertidumbre de la demanda, la tarifa, el costo variable por pasajero y el precio del combustible, y qué riesgo de pérdidas implica?

| Alternativa | Interpretación | Capacidad anual supuesta |
|---|---|---:|
| A | Mantener capacidad de referencia | 100,000 pasajeros |
| B | Aumentar frecuencias con aeronaves de referencia | 125,000 pasajeros |
| C | Cambiar a una aeronave de mayor capacidad y menor consumo por asiento | 115,000 pasajeros |

Las cifras de capacidad se usan como máximo anual de pasajeros atendibles. Los costos fijos y litros por asiento ofertado también son hipótesis configurables en `src/aeromexico_montecarlo/modelo.py`.

## Modelo

Para cada iteración y alternativa:

```text
pasajeros atendidos = mínimo(demanda anual, capacidad anual)
combustible anual = capacidad anual × litros por asiento ofertado × precio del combustible
utilidad anual = pasajeros atendidos × (tarifa − costo variable por pasajero)
                − combustible anual − costo fijo anual
```

El costo de combustible se aplica a la capacidad ofertada, aunque queden asientos vacíos. De ese modo, las alternativas con más oferta asumen también el costo de operar esa capacidad. La demanda alta puede tener tarifas más elevadas que la demanda baja. Demanda y tarifa comparten el mismo régimen (bajo, medio o alto); costo variable y precio del combustible se muestrean de forma independiente en el ejemplo.

### Supuestos aleatorios por iteración

- **Régimen de demanda:** bajo (25 %), medio (50 %) o alto (25 %). Las probabilidades se validan y deben sumar exactamente 1 dentro de una tolerancia numérica.
- **Demanda anual:** distribución triangular por régimen. Rangos mínimo, moda y máximo: 65,000/82,000/100,000; 82,000/105,000/130,000; y 105,000/132,000/160,000 pasajeros.
- **Tarifa promedio:** uniforme por régimen: MXN 3,500–4,300 (bajo), MXN 4,000–5,000 (medio) y MXN 4,500–5,600 (alto).
- **Costo variable por pasajero:** triangular, mínimo/moda/máximo de MXN 650/850/1,100.
- **Precio de combustible:** triangular, mínimo/moda/máximo de MXN 17/23/34 por litro.

Los supuestos se concentran en `Supuestos` y `ALTERNATIVAS` para que puedas cambiarlos sin modificar las fórmulas. La semilla fija hace que cada ejecución produzca los mismos escenarios con las versiones indicadas.

### Métricas de comparación

- **VME:** promedio de utilidad anual simulada; es el criterio principal de comparación.
- **Mediana y desviación estándar:** centro y dispersión de la utilidad.
- **Probabilidad de pérdida:** proporción de iteraciones con utilidad menor a cero.
- **VaR 5 %:** percentil 5 de utilidad; 5 % de las iteraciones queda por debajo de este valor.
- **CVaR 5 %:** utilidad promedio de las iteraciones en la cola inferior del 5 %.
- **Punto de equilibrio:** pasajeros necesarios para cubrir el costo fijo y el combustible de referencia con la tarifa y el costo variable de referencia. También se indica si ese volumen cabe dentro de la capacidad.
- **Sensibilidad:** cambios de ±10 % y ±20 % en demanda, tarifa y combustible. Cada shock se evalúa con los mismos escenarios base, de modo que la diferencia del VME se pueda atribuir al cambio aplicado.

El punto de equilibrio usa valores de referencia (tarifa MXN 4,600, costo variable MXN 850 y combustible MXN 25/litro), no el promedio de todas las distribuciones. No sustituye al resultado probabilístico.

## Estructura

```text
src/modelo.py       Supuestos, generación de escenarios, utilidades y métricas
src/run_model.py    Ejecución completa, exportación de resultados y gráficos
tests/              Pruebas de fórmulas, semilla, riesgos y validación
results/            CSV y gráficos que genera el programa
requirements.txt    Versiones compatibles con Python 3.10
```

## Requisitos

- Python **3.10**
- `pip`
- Dependencias de `requirements.txt` (NumPy, pandas, Matplotlib y pytest)

## Cómo ejecutarlo

Abre una terminal en la carpeta del proyecto y crea un entorno virtual:

```bash
python3.10 -m venv .venv
```

Actívalo en macOS/Linux:

```bash
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instala dependencias:

**`pyproject.toml`**, install the project with:
```bash
pip install -e .
```

Ejecuta las 10,000 iteraciones y genera los resultados:

```bash
python src/run_model.py
```

Las tablas y gráficas se guardan en `src/aeromexico_montecarlo/results`. El programa también imprime el VME, las métricas de riesgo y el punto de equilibrio en la terminal.

Para correr las pruebas:

```bash
python -m pytest -q
```

## Archivos generados

- `escenarios_simulados.csv`: 10,000 combinaciones de demanda, tarifa y costos.
- `utilidades_por_iteracion.csv`: utilidad anual por iteración y alternativa.
- `resumen_resultados.csv`: VME y métricas de riesgo.
- `punto_equilibrio.csv`: pasajeros de equilibrio y factibilidad por capacidad.
- `sensibilidad.csv`: VME bajo cada perturbación de sensibilidad.
- `distribucion_utilidades.png`: distribución de la utilidad anual.
- `vme_alternativas.png`: comparación visual del VME.
- `sensibilidad_vme.png`: cambio del VME bajo shocks de ±10 % y ±20 %.

## Resultado de la corrida incluida

Con 10,000 iteraciones y semilla 42, la alternativa C obtuvo un VME aproximado de **MXN 141.6 millones** y una probabilidad de pérdida de **6.9 %**. La alternativa A obtuvo MXN 133.3 millones y 2.9 % de probabilidad de pérdida; la alternativa B, MXN 120.3 millones y 16.2 %. Bajo los valores de referencia, los puntos de equilibrio fueron aproximadamente 56,667 pasajeros (A), 70,200 (B) y 61,667 (C). Estos resultados son reproducibles con los supuestos del proyecto y no deben interpretarse como cifras reales de Aeroméxico.

## Lectura de resultados y limitaciones

La alternativa con el VME mayor maximiza la utilidad promedio bajo estos supuestos. Conviene leerla junto con la probabilidad de pérdida y el CVaR: dos opciones con VME parecido pueden tener resultados desfavorables muy distintos. El resultado no constituye una recomendación operativa para Aeroméxico.

El modelo simplifica una operación aérea real. No incorpora conexiones de red, estacionalidad mensual, restricciones de flota y tripulación, mantenimiento, impuestos, financiamiento, ingresos por carga, competencia, cancelaciones, restricciones aeroportuarias ni una curva de demanda estimada con datos observados. Tampoco calibra las distribuciones con datos de una ruta real. Antes de usarlo para una decisión empresarial, se necesitarían datos internos, validación con expertos y pruebas de escenarios más detalladas.

# Author

**Sidhartha Manríquez**

Data Architecture | Data Platforms | Financial Analytics Engineering


### License

This project is licensed under the terms specified in the **[LICENSE](LICENSE)** file.
