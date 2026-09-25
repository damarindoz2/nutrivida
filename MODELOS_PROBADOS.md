# Registro de modelos probados

Todos los modelos se prueban con información disponible hasta una fecha de
corte. Después se comparan contra la demanda que realmente ocurrió. Un modelo
no se descarta sólo porque “se vea mal”, sino por sus métricas y sus
limitaciones operativas.

**Nivel principal revisado:** la elección final se hará por `Fecha + SKU`, que
es el nivel del pronóstico empresarial y del inventario central. Las métricas
por `SKU + Región` se conservarán como diagnóstico del desglose regional, pero
no decidirán por sí solas el modelo total. La elección regional anterior se
considera provisional hasta terminar esta nueva comparación.

## Qué significa “pronóstico de la empresa”

No es un modelo creado ni estimado en este análisis. Es el valor que NutriVida
entregó en la columna `Pronostico_Empresa` de la hoja `Pronostico vs Real`.
Como no se recibió la fórmula, los parámetros ni el procedimiento con el que se
calculó, no se intentó asignarle un nombre estadístico. Se utilizó como comparador del
proceso actual, frente a la misma demanda limpia y al mismo nivel `Fecha + SKU`.

En las dos ventanas activas de 2025 obtuvo WAPE 19.22% y sesgo +7.69%. Esto no
explica cómo lo construyeron; únicamente mide cómo se comportaron los valores
que entregaron frente a lo ocurrido.

## 1. Repetir el último mes

**Fórmula:**

`Pronóstico futuro = último dato conocido de cada SKU y región`

**Prueba:** datos hasta diciembre de 2024; evaluación enero-junio de 2025.

- WAPE: 25.07%.
- Sesgo: -9.46%.
- Agregado al nivel SKU: WAPE 22.31% y sesgo -9.46%.

**Aprendizaje:** el modelo es una referencia mínima fácil de explicar, pero
supone que la demanda no cambia. Ignora tendencia, estacionalidad y diferencias
entre los meses del horizonte.

**Decisión:** descartado como modelo final. Al mismo nivel y semestre, su WAPE
de 22.31% es peor que el 19.68% de la empresa y además tiende a quedarse corto.
Se conserva como línea base para comprobar que los métodos posteriores realmente
aportan valor.

## 2. Promedio de los últimos tres meses

**Fórmula:**

`Pronóstico futuro = promedio de los tres últimos datos de cada SKU y región`

**Prueba:** datos hasta diciembre de 2024; evaluación enero-junio de 2025.

- WAPE: 20.35%.
- Sesgo: -8.18%.
- Mejora de WAPE contra último mes: 4.72 puntos porcentuales.
- Agregado al nivel SKU: WAPE 17.98% y sesgo -8.18%.

**Aprendizaje:** utilizar tres meses reduce la dependencia de un diciembre
inusual. Sin embargo, el mismo promedio todavía se repite durante los seis meses
futuros. No distingue enero de junio y no captura el crecimiento estacional
observado en varias series.

**Decisión:** descartado como modelo final aunque, agregado al mismo nivel y
semestre, mejora el WAPE empresarial de 19.68% a 17.98%. A nivel regional su
WAPE es 20.35%, mantiene un sesgo negativo importante y repite el mismo valor en
los seis meses. Se conserva como componente de nivel reciente para el modelo
combinado.

## 3. Mismo mes del año anterior

**Fórmula:**

`Pronóstico de cada mes = demanda del mismo SKU en ese mes del año anterior`

Ejemplo: enero de 2025 utiliza enero de 2024; febrero de 2025 utiliza febrero de
2024.

**Primera prueba:** datos hasta diciembre de 2024; evaluación enero-junio de
2025, al nivel principal por SKU.

- WAPE: 11.46%.
- Sesgo: -5.47%.
- Pronóstico empresarial en el mismo nivel y semestre: WAPE 19.68% y sesgo
  +4.23%.
- Fechas de referencia posteriores al corte: cero.

**Aprendizaje:** el modelo reconoce que enero y junio pueden tener niveles
distintos y mejora claramente tanto las dos líneas base como el pronóstico
empresarial. Su riesgo es copiar eventos excepcionales del año anterior y no
adaptarse bien a cambios recientes de tendencia.

**Decisión provisional:** continúa como alternativa; no se descarta. Debe probarse
también en julio-diciembre de 2025 y compararse con el promedio estacional y el
modelo ponderado antes de elegirlo.

## 4. Promedio estacional

**Fórmula:**

`Pronóstico de cada mes = promedio de ese mismo mes en todos los años anteriores disponibles`

Para enero de 2025 utiliza el promedio de enero de 2023 y enero de 2024. El
procedimiento se repite para cada SKU y mes calendario.

**Primera prueba:** datos hasta diciembre de 2024; evaluación enero-junio de
2025, al nivel principal por SKU.

- WAPE: 12.23%.
- Sesgo: -7.37%.
- Pronósticos vacíos: cero.
- Mismo mes del año anterior: WAPE 11.46% y sesgo -5.47%.
- Pronóstico empresarial: WAPE 19.68% y sesgo +4.23%.

**Aprendizaje:** promediar varios años suaviza eventos particulares, pero
también puede quedarse atrás cuando la demanda cambia de nivel. En este semestre
fue ligeramente menos preciso y subestimó más que utilizar únicamente el año
anterior.

**Decisión provisional:** no es la alternativa principal como modelo aislado. Se
mantiene hasta revisar el segundo semestre y como fuente de estacionalidad para
una combinación ponderada.

## 5. Nivel reciente ponderado por índice estacional

**Fórmula:**

1. Calcular por SKU un índice para cada mes:
   `promedio del mes / promedio general`.
2. Quitar temporalmente la estacionalidad de los últimos tres meses:
   `demanda / índice del mes`.
3. Calcular el nivel reciente con pesos 20%, 30% y 50%, dando más importancia al
   último mes.
4. Pronosticar cada mes futuro como:
   `nivel reciente × índice estacional del mes futuro`.

**Primera prueba:** datos hasta diciembre de 2024; evaluación enero-junio de
2025, al nivel principal por SKU.

- WAPE: 11.24%.
- Sesgo: -5.37%.
- Mismo mes del año anterior: WAPE 11.46% y sesgo -5.47%.
- Todos los grupos sumaron exactamente 100% de peso.
- Índices estacionales vacíos o no positivos: cero.

**Aprendizaje:** separar nivel y temporada permite utilizar la información
reciente sin pronosticar lo mismo para todos los meses. Con los pesos iniciales
20%-30%-50%, el modelo mejora ligeramente tanto WAPE como sesgo frente al mismo
mes del año anterior.

**Decisión provisional:** continúa como mejor alternativa de la primera ventana,
pero la mejora es pequeña —0.22 puntos de WAPE—. Los pesos todavía no se
consideran definitivos y el modelo debe validarse en julio-diciembre de 2025 sin
ajustarlos usando ese segundo periodo.

### Validación sin cambiar los pesos

Se mantuvieron exactamente los pesos 20%-30%-50%. Con información disponible
hasta junio de 2025 se pronosticó julio-diciembre.

- Ponderado incluyendo la pausa de Azúcar: WAPE 15.63%, sesgo +5.95%.
- Ponderado solamente para SKU activos: WAPE 12.17%, sesgo +2.50%.
- Mismo mes anterior para SKU activos: WAPE 11.72%, sesgo -5.68%.

El caso de Azúcar confirma que un modelo estadístico no puede anticipar por sí
solo una descontinuación o pausa operativa. Esa excepción requiere una regla de
negocio separada.

### Resultado conjunto de las dos ventanas activas

| Modelo | WAPE | Sesgo |
| --- | ---: | ---: |
| Mismo mes anterior | 11.59% | -5.57% |
| Ponderado estacional 20%-30%-50% | 11.71% | -1.45% |

**Interpretación:** el mismo mes anterior gana por 0.12 puntos de WAPE. El
ponderado queda mucho más cerca de sesgo cero y, por tanto, presenta menor
tendencia a quedarse corto. Ambos permanecen como finalistas hasta experimentar
con los pesos usando una separación explícita entre selección y validación.

## 6. Ponderado con promociones separadas y pesos seleccionados

**Tratamiento promocional:** las unidades históricas marcadas en promoción se
dividen entre el factor promocional estimado del SKU para aproximar una demanda
base. Si se recibe una promoción futura, la proporción de combinaciones
canal-región promocionadas se convierte en un multiplicador separado.

La auditoría mostró que las promociones no son marginales:

- Octubre-diciembre de 2024: 52 filas promocionales y 23 de 25 SKU involucrados.
- Abril-junio de 2025: 48 filas promocionales y 21 de 25 SKU involucrados.

**Selección de pesos:** se probaron combinaciones en pasos de 10%, exigiendo que
los meses recientes no tuvieran menor peso que los antiguos. Los pesos se
eligieron únicamente con enero-junio de 2025. Entre los modelos a no más de 0.5
puntos del mejor WAPE se priorizó la menor subestimación.

**Pesos seleccionados:** 0% para el más antiguo, 50% para el intermedio y 50%
para el más reciente. En la primera ventana esta misma combinación obtuvo tanto
el menor WAPE como la menor subestimación entre las alternativas cercanas.

**Validación sin cambiar pesos:**

| Periodo | WAPE | Sesgo | Subestimación |
| --- | ---: | ---: | ---: |
| Enero-junio 2025 | 8.93% | -5.36% | 7.14% |
| Julio-diciembre 2025, SKU activos | 7.26% | +0.50% | 3.38% |
| Ambas ventanas activas | 8.10% | -2.44% | 5.27% |

En ambas ventanas la sobreestimación fue 2.83%. Como comparación, el mismo mes
anterior obtuvo WAPE 11.59% y subestimación 8.58%; la empresa obtuvo WAPE 19.22%
y subestimación 5.76%.

**Decisión provisional:** es el mejor modelo si se conoce el calendario de
promociones. Reduce tanto el error total como la demanda que queda por debajo.
No se debe presentar el WAPE de 8.10% como alcanzable para 2026 sin información
promocional futura. Sin calendario, deben mostrarse por separado la demanda base
y un escenario promocional editable.

## 7. Modelo final: promedio reciente, estacionalidad y promociones recurrentes

Para reproducir de forma realista la información disponible al generar 2026, se repitió el
backtest sin utilizar las promociones reales del periodo futuro. Este modelo no
consiste únicamente en “recurrencia”: primero normaliza promociones históricas,
calcula estacionalidad por SKU, promedia los dos meses comparables más recientes y
recupera el efecto del mes futuro. La recurrencia es sólo la última regla: una
campaña se proyecta si el mismo SKU y mes tuvo promoción en al menos dos años
conocidos al momento del corte.

| Periodo | WAPE | Sesgo |
| --- | ---: | ---: |
| Enero-junio 2025 | 11.68% | -7.82% |
| Julio-diciembre 2025, SKU activos | 9.44% | -2.86% |
| Ambas ventanas activas | 10.56% | -5.35% |

En ambas ventanas, la subestimación fue 7.96% y la sobreestimación 2.61%.

**Decisión:** esta es la métrica comparable con el escenario recomendado 2026.
Su WAPE de 10.56% mejora al mismo mes anterior —11.59%— y a la empresa —19.22%—,
pero no alcanza el 8.10% del escenario ideal con calendario confirmado. La cifra
que debe presentarse como validación realista es 10.56%.

## 8. Escenario de protección contra sesgo negativo

No es otro pronóstico de demanda, sino un colchón visible sobre el modelo de
recurrencia. Se probaron 0%, 2%, 4%, 6%, 8% y 10% utilizando enero-junio para
elegir el porcentaje cuyo sesgo quedara más cerca de cero. Se seleccionó 8% y se
conservó fijo para julio-diciembre.

| Periodo | WAPE | Sesgo | Subestimación | Sobreestimación |
| --- | ---: | ---: | ---: | ---: |
| Enero-junio 2025 | 10.50% | -0.45% | 5.47% | 5.03% |
| Julio-diciembre 2025 | 10.72% | +4.91% | 2.91% | 7.81% |
| Ambas ventanas | 10.61% | +2.22% | 4.19% | 6.42% |

**Decisión:** mantenerlo como `Pronostico_Protegido`, no como reemplazo del
recomendado. Sacrifica 0.05 puntos de WAPE total, pero disminuye notablemente la
subestimación cuando evitar faltantes tiene mayor costo o prioridad.

## Pasos pendientes

9. Sustituir promociones recurrentes por el calendario de promociones si se
   proporciona.
