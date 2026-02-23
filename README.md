# Ciberfísica e Inteligencia Artificial Aplicada (INF-2602)

Este repositorio reúne **prácticas, notebooks y proyectos** de la asignatura **Ciberfísica e Inteligencia Artificial Aplicada** (Ingeniería Mecatrónica). El enfoque es construir y comprender un **Sistema Ciberfísico (CPS)** de extremo a extremo, conectando el mundo físico con la capa digital y cerrando el ciclo con **decisiones basadas en datos**:

**Sensado → adquisición → preprocesamiento → dataset → modelo → evaluación → inferencia → acción**

Aquí encontrarás un camino progresivo desde fundamentos de arquitectura CPS y flujo de datos, hasta **modelos de Machine Learning supervisado** (regresión/clasificación) y su **integración en un pipeline funcional** con evidencias técnicas reproducibles.

---

## Objetivos técnicos del repositorio

- Diseñar un **pipeline CPS mínimo viable** (telemetría, registros, trazabilidad y estructura de datos).
- Construir datasets **limpios y documentados** (CSV/JSON), con criterios de calidad y versionado.
- Entrenar y evaluar modelos ligeros con métricas estándar:
  - **Regresión:** MAE, RMSE, R²
  - **Clasificación:** Accuracy, Precision, Recall, F1, matriz de confusión
- Integrar **inferencia en PC** (o simulación) para tomar decisiones en tiempo cercano a real.
- Documentar resultados con estilo ingenieril: bitácora, tablas de pruebas, gráficas y conclusiones.

---

## Contenido por unidades (progresión didáctica)

### U1 — Fundamentos de CPS y flujo de datos
- Arquitectura base (capas físico/digital, interfaces y ciclo de retroalimentación)
- Captura de señales y consideraciones de muestreo
- Telemetría ligera (p. ej., HTTP/MQTT) y registro estructurado
- Evidencias: diagramas, bitácora y pruebas de comunicación

### U2 — Datos: calidad, estructura y trazabilidad
- EDA (análisis exploratorio), limpieza y transformación
- Manejo de valores faltantes, ruido y atípicos
- Definición de *schema* y documentación tipo “datasheet del dataset”
- Evidencias: reporte de calidad, tablas de validación y dataset versionado

### U3 — Modelado supervisado y evaluación
- Baselines y modelos interpretables (árboles, regresión, clasificación)
- Separación train/test y validación simple
- Ajuste de hiperparámetros (básico) y análisis de error
- Evidencias: notebooks reproducibles y comparativas de métricas

### U4 — Integración: inferencia y proyecto CPS + IA
- Pipeline operativo adquisición → preproceso → inferencia → salida
- Pruebas por escenarios y criterios de aceptación
- Proyecto integrador (en simulación o gemelo digital)
- Evidencias: demo, reporte técnico, y repositorio final ordenado

---

## Estructura sugerida del repositorio

```text
00_setup/                 # entorno, dependencias, guías rápidas
01_cps_pipeline/          # sensado, muestreo, telemetría, logging
02_data_quality/          # EDA, limpieza, datasheet, versionado
03_ml_models/             # regresión/clasificación, métricas, comparativas
04_inference_integration/ # scripts de inferencia y pruebas
05_project/               # proyecto final + reportes + evidencias
utils/                    # funciones y herramientas reutilizables
