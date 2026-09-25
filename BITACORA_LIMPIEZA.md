# Bitácora de limpieza de datos

Este archivo registra qué se revisó, qué se decidió y qué falta. El objetivo es
poder explicar y reproducir el proceso.

## 1. Estructura inicial del archivo

- Se identificaron cinco hojas: `Resumen Gerencia`, `Ventas Historicas`,
  `Pronostico vs Real`, `Inventario y Quiebres` y `Precios y Costos`.
- `Ventas Historicas` contenía 8,114 filas antes de limpiar.
- La combinación esperada de 36 meses, 25 SKU, 3 canales y 3 regiones produce
  8,100 filas.

## 2. Nombres de canales

- Se detectaron distintas formas de escribir los mismos canales.
- `E-commerce` se unificó como `Ecommerce`.
- `Super` y `SUPERMERCADO` se unificaron como `Supermercado`.
- `Ecommerce` y `Supermercado` se conservaron como canales distintos; no se
  mezclaron sus ventas. Después de retirar duplicados quedaron 2,700 filas de
  Ecommerce, 2,700 de Mayorista y 2,700 de Supermercado.

## 3. Filas duplicadas

- Se encontraron 28 filas involucradas en duplicados exactos, equivalentes a 14
  copias adicionales.
- Se conservó una aparición de cada fila.
- Resultado: 8,100 filas y ninguna clave `Fecha + SKU + Canal + Region`
  repetida.

## 4. Fechas

- No se encontraron fechas inválidas.
- El historial comprende enero de 2023 a diciembre de 2025: 36 meses.
- `Fecha` se convirtió a un tipo de fecha para ordenar y comparar correctamente.

## 5. Precios unitarios vacíos

- Se encontraron 19 precios vacíos.
- Para cada caso se comprobó el precio del mismo SKU en las ventas y en la hoja
  maestra `Precios y Costos`.
- Cada SKU tiene un solo precio y todos coinciden con el catálogo maestro.
- Los 19 precios se completaron desde el catálogo y quedaron marcados con
  `Precio_Fue_Completado`.
- Resultado: cero precios vacíos.

## 6. Unidades negativas

- Se encontraron 9 filas con unidades negativas.
- Al comparar con `Venta_Real`, se comprobó que los consolidados trataban esas
  cantidades como cero, no como ventas que debían restarse.
- Se guardó el valor original, se marcaron las filas corregidas y se sustituyeron
  los negativos por cero en la tabla de trabajo.
- Resultado: cero unidades negativas. El impacto de la corrección fue de 7,378
  unidades.

## 7. Ceros originales de Azúcar

- Los 54 ceros originales pertenecen al `SKU-1021` durante julio-diciembre de
  2025: las 9 combinaciones de canal y región durante 6 meses.
- Se conservaron porque las hojas coinciden en que no hubo ventas.
- El SKU se considera inactivo o en pausa desde julio de 2025, sin afirmar que
  fue descontinuado.
- Su pronóstico base será cero, con una opción manual de reactivación.

## 8. Stock final y venta perdida

- Cuando quedó stock al final del mes, no se registró venta perdida.
- Cuando el stock llegó a cero, se registró venta perdida.
- La excepción son cinco meses del `SKU-1021` en pausa, con stock y venta perdida
  iguales a cero.
- Los valores se conservaron porque presentan un patrón operativo coherente.
- En las 875 filas se comprobó que `Stock_Final` es el máximo entre stock inicial
  menos venta real y cero.
- También se comprobó que `Venta_Perdida_Unid` es el máximo entre venta real
  menos stock inicial y cero.
- Dentro de la lógica del archivo, `Venta_Real` ya representa la demanda total y
  la venta perdida es la parte no atendida. No deben sumarse.
- Las unidades atendidas se pueden obtener como `Venta_Real - Venta_Perdida_Unid`.

## 9. Unidades vacías

- Permanecen 28 celdas vacías en `Unidades`; no se consideran equivalentes a
  cero.
- Las otras hojas suman únicamente las unidades conocidas, así que no permiten
  recuperar los valores originales.
- La columna original no se modificó.
- Se creó `Unidades_Modelo` para los valores utilizados por el modelo y
  `Unidad_Fue_Estimada` para identificar cada estimación.

Se probaron tres métodos sobre 7,518 valores conocidos:

1. **Temporal:** interpolación entre valores conocidos de la misma combinación
   SKU, canal y región. Este método también permite tratar vacíos consecutivos.
2. **Estacional:** promedio del mismo mes de todos los demás años disponibles
   para la misma combinación.
3. **Combinado:** promedio de la estimación temporal y la estacional.

Los WAPE obtenidos fueron 19.96%, 21.08% y 18.51%, respectivamente. En las filas
sin promoción, el combinado también fue el mejor con 15.92%.

Las promociones requirieron un tratamiento adicional:

- Se estimó primero una demanda base excluyendo promociones.
- El factor promocional mediano global fue 1.7446.
- Los factores aprendidos con 2023-2024 se validaron sobre 171 promociones de
  2025.
- El ajuste redujo el WAPE promocional de 46.83% a 18.02%.
- Para los tres SKU con vacíos promocionales, los WAPE ajustados quedaron entre
  11.43% y 13.42%.

Casos especiales:

- En el inicio o final del historial se utilizó el método estacional,
  porque no existen dos extremos para interpolar.
- Si solo existe un año comparable, se considera una estimación de menor
  respaldo.
- Los ceros de `SKU-1021` desde julio de 2025 no se usarán como referencia.
- Las promociones permanecen sujetas a mayor incertidumbre porque no se conoce
  su tipo, intensidad ni duración.

Resultado final:

- 23 vacíos completados con el promedio temporal-estacional.
- 3 vacíos promocionales completados con la demanda base multiplicada por el
  factor mediano del SKU.
- 2 extremos completados con la referencia estacional.
- `Unidades` conserva 28 vacíos y `Unidades_Modelo` tiene cero.
- Las 28 estimaciones están identificadas con `Unidad_Fue_Estimada`.
- El total incorporado mediante estimación es 21,372.19 unidades.

## 10. Consistencia del catálogo

- Se revisaron 25 SKU y 25 productos.
- Cada SKU tiene un único producto y una única categoría.
- Cada producto tiene un único SKU y una única categoría.
- No se requirieron correcciones y las tres columnas pueden utilizarse para
  segmentar los pronósticos.

## 11. Valores extremos de unidades

- El método IQR detectó 292 extremos: 250 promocionales y 42 sin promoción.
- Las promociones se conservaron como eventos especiales y no se trataron como
  errores automáticos.
- Los extremos bajos en cero corresponden a negativos ya tratados; los otros
  extremos sin promoción, salvo uno, están cerca de sus límites y se conservaron.
- Se investigó `SKU-1001`, Supermercado, Norte, marzo de 2025: 13,380 unidades
  sin promoción.
- El dato se propagó al consolidado y al inventario, pero las otras hojas no son
  una confirmación independiente.
- La estimación temporal fue 1,597, la estacional 1,469.5 y la combinada
  1,533.25.
- `Unidades` conserva 13,380 y `Unidades_Modelo` utiliza 1,533.25. La fila queda
  marcada con `Unidad_Fue_Ajustada_Atipico`.
- No se afirma que el valor correcto fuera 1,380; se utiliza una estimación
  reproducible para el modelo.
- El ajuste reduce 11,846.75 unidades. El impacto neto, después de considerar
  también los vacíos estimados, es de 9,525.44 unidades.

## 12. Claves de las otras hojas

- `Pronostico vs Real`: 875 filas, 875 claves únicas `Fecha + SKU` y cero
  duplicados.
- `Inventario y Quiebres`: 875 filas, 875 claves únicas `Fecha + SKU` y cero
  duplicados.
- Ambas hojas contienen exactamente las mismas combinaciones de 35 meses y 25
  SKU.
- `Precios y Costos`: 25 filas, 25 SKU únicos y cero duplicados.
- No fue necesario retirar ninguna fila de estas hojas.

## 13. Reconciliación de ventas

- `Venta_Sistema` coincide exactamente con `Venta_Real` en los 875 SKU-meses.
- El consolidado se generó desde el detalle original: incluyó duplicados y el
  valor atípico, omitió vacíos y trató negativos como cero.
- El sistema y el consolidado suman 7,305,668 unidades.
- Retirar duplicados afectó 13 SKU-meses y redujo 10,936 unidades.
- La venta limpia antes de estimaciones suma 7,294,732 unidades.
- En los 35 meses comparables, estimaciones y ajuste atípico tienen un efecto
  neto de 9,207.44 unidades.
- `Venta_Modelo` suma 7,303,939.44: 1,728.56 unidades menos que el consolidado.
- Existen 40 SKU-meses afectados: 13 por duplicados, 26 por estimaciones y uno
  por el valor atípico.
- Se conservará `Venta_Real` como cifra reportada y se usará `Venta_Modelo` para
  análisis y pronóstico.

## 14. Reconciliación de inventario

- `Venta_Real` coincide entre pronóstico e inventario en los 875 SKU-meses.
- Se conservaron los valores originales y se creó un escenario recalculado con
  `Venta_Modelo`.
- Los quiebres pasan de 187 a 185 SKU-meses.
- La venta perdida pasa de 201,617 a 190,050.05 unidades.
- La venta atendida pasa de 7,104,051 a 7,113,889.39 unidades.

## 15. Días de cobertura y servicio

- Las 875 coberturas coinciden con `Stock_Final / Venta_Real × 30`, redondeado a
  un decimal.
- Los seis vacíos corresponden a demanda cero.
- Servicio por unidades original: 97.24% histórico y 97.02% en 2025.
- Servicio por unidades limpio: 97.40% histórico y 97.49% en 2025.
- SKU-meses sin venta perdida: 78.63% histórico y 79.67% en 2025.
- Ninguna fórmula reproduce exactamente el 96% declarado.

## 16. Márgenes, costos y rotación

- `Margen_Bruto_pct` es un porcentaje decimal válido en los 25 SKU.
- No hay precios, costos de almacenaje ni vidas útiles no positivos.
- Ingreso atendido 2025: USD 11,036,458.00.
- Margen bruto 2025: USD 3,406,163.35; margen ponderado 30.86%.
- Costo anual estimado de almacenaje: USD 276,466.30.
- La rotación estándar aproximada es 11.03, no 5.1. La cifra declarada requiere
  definición y costos contables no incluidos en el archivo.

## 17. Resumen Gerencia y promociones

- Venta total declarada: USD 12,344,981.
- Suma regional declarada: USD 11,398,874.
- Diferencia interna: USD 946,107.
- Ingreso calculado desde el sistema: USD 11,399,329.07.
- Demanda limpia valuada: USD 11,345,787.06.
- Venta atendida: USD 11,036,458.00.
- El total gerencial no puede reconciliarse con las demás cifras.
- `Promocion` no informa tipo, descuento, intensidad ni duración. Las campañas
  futuras necesitarán un calendario de promociones o un ajuste manual.

## Siguiente paso

## 18. Evaluación histórica del pronóstico

- Se construyeron 75 series mensuales: 25 SKU por 3 regiones.
- Se utilizaron dos ventanas de prueba de seis meses: enero-junio y
  julio-diciembre de 2025.
- Pronóstico empresarial 2025, sin pausa de Azúcar: WAPE 19.22% y sesgo +7.69%.
- Al nivel SKU-región, el promedio estacional obtuvo WAPE 15.17% y sesgo -7.20%.
- El combinado obtuvo WAPE 15.37% y sesgo -4.38%.
- Se eligió el combinado por su equilibrio entre precisión y menor riesgo de
  subestimar.

## 19. Pronóstico enero-junio de 2026

- Se generaron 450 filas: 6 meses por 25 SKU por 3 regiones.
- Pronóstico base: 1,209,577.95 unidades.
- Escenario de protección: 1,264,931.09 unidades.
- Factor de protección: 1.0458, derivado del sesgo del backtest.
- `SKU-1021` queda en cero en 18 filas y requiere reactivación manual.
- Se generó `Pronostico_NutriVida_2026.xlsx` con histórico limpio, detalle,
  resúmenes y validación de modelos.

## 20. Dashboard

- Se creó `dashboard.py` y `requirements.txt`.
- Se instalaron y probaron Streamlit y Plotly dentro de `.venv`.
- La aplicación carga el caso validado o recibe otro `.xlsx` con la misma
  plantilla mínima.
- Incluye filtros, escenario base/protección, ajuste porcentual, ajuste absoluto,
  exclusión de una selección, gráficas y descarga.
- La prueba automática del dashboard terminó sin excepciones.

## Siguiente paso

1. Repasar `GUIA_REPASO.md` y ejecutar el dashboard al menos una vez.
2. Probar tres escenarios: subir una región 10%, excluir un SKU y
   reactivar Azúcar con unidades manuales.
3. Preparar la explicación de las tres limitaciones de negocio pendientes.

## 21. Revisión del nivel, pesos y promociones

- El nivel principal cambió de SKU-región a SKU para coincidir con el
  pronóstico empresarial y el inventario central.
- Se conservaron las regiones como desglose reconciliado.
- Se separaron subestimación y sobreestimación para priorizar el riesgo de
  ventas perdidas.
- Se normalizaron promociones históricas mediante factores por SKU.
- Se probaron pesos crecientes en pasos de 10% usando enero-junio para seleccionar
  y julio-diciembre para validar.
- La prueba eligió pesos 0%-50%-50%, que equivalen simplemente a promediar los
  dos meses comparables más recientes.
- Con calendario promocional conocido, la validación activa obtuvo WAPE 8.10%,
  sesgo -2.45%, subestimación 5.31% y sobreestimación 2.86%.
- Al validar la regla real de recurrencia histórica sin conocer las campañas
  futuras, se obtuvo WAPE 10.56%, sesgo -5.35%, subestimación 7.96% y
  sobreestimación 2.61%. Esta es la validación que corresponde al escenario
  recomendado actual; 8.10% queda como escenario ideal con calendario confirmado.

## 22. Pronóstico revisado 2026

- Se definió recurrencia como promoción del mismo SKU y mes en al menos dos años.
- Se encontraron 58 combinaciones recurrentes; 56 permanecen activas después de
  aplicar la pausa de Azúcar.
- Base sin promoción: 1,192,504.69 unidades.
- Recomendado con recurrencia: 1,224,820.00 unidades.
- Se generaron 150 filas SKU y 450 filas regionales.
- La suma regional coincide con el total SKU, salvo precisión decimal inferior a
  0.000000000004 unidades.
- Archivo creado originalmente como `Pronostico_NutriVida_2026_REVISADO.xlsx`;
  la entrega vigente se organizó después como
  `resultados/Pronostico_NutriVida_2026_FINAL.xlsx`.

## 23. Escenario de protección contra subestimación

- Se probaron protecciones de 0%, 2%, 4%, 6%, 8% y 10% sobre el pronóstico
  recurrente.
- Se eligió 8% con enero-junio de 2025 porque dejó el sesgo más cerca de cero.
- El mismo porcentaje se validó sin cambios en julio-diciembre.
- En ambas ventanas obtuvo WAPE 10.61%, sesgo +2.22%, subestimación 4.19% y
  sobreestimación 6.42%.
- El recomendado sin colchón conserva WAPE 10.56%, sesgo -5.35%, subestimación
  7.96% y sobreestimación 2.61%.
- `Pronostico_Protegido` se conserva como escenario separado y no sustituye
  automáticamente a `Pronostico_Final`.
- Total protegido enero-junio de 2026: 1,322,805.60 unidades.

## 24. Robustez por segmento y actualización del dashboard

- Se generaron `Robustez_SKU_2025.csv`, `Robustez_Categoria_2025.csv` y
  `Robustez_Mes_2025.csv`.
- El protegido redujo subestimación en 25 de 25 SKU y mejoró WAPE en 13 de 25.
- Galletas mejoró WAPE de 12.40% a 10.88% y Despensa de 9.82% a 9.80%; Bebidas
  y Lácteos cambiaron el riesgo, pero no mejoraron su WAPE.
- El dashboard consume `resultados/Pronostico_NutriVida_2026_FINAL.xlsx`.
- Permite comparar base sin promoción, recomendado y protegido 8%.
- Incluye una vista de robustez por SKU, categoría y mes, con gráfica contra la
  diagonal y tabla de errores.
- Las pruebas automáticas del escenario protegido y las tres segmentaciones
  terminaron sin excepciones.

## 25. Rediseño narrativo del dashboard

- Se reorganizó en seis pestañas siguiendo el orden real del análisis.
- La limpieza muestra problema, hallazgo, decisión y justificación.
- Se incorporaron reconciliaciones, supuestos y limitaciones de negocio.
- Los modelos preliminares y finales tienen tablas de WAPE, sesgo,
  subestimación y sobreestimación.
- Los tres escenarios 2026 permanecen visibles y el selector actualiza KPI,
  historia y descarga.
- Se verificó automáticamente que recomendado, protegido y ajuste manual
  cambian de 1,224,820 a 1,322,806 y 1,455,086 unidades, respectivamente.
- Las seis pestañas, siete gráficas y vistas de robustez terminaron sin errores.

## 26. Detalle de modelos por SKU y mes

- Se creó `Detalle_Validacion_Modelos_2025.csv` con 294 comparaciones completas.
- Se creó `Trazabilidad_Pronostico_2026.csv` con 150 pronósticos y sus ventas del
  mismo mes en los tres años anteriores.
- No quedaron pronósticos ni antecedentes vacíos en estas tablas.
- El dashboard permite seleccionar categoría, SKU y mes, comparar cada modelo,
  identificar el menor error y descargar el detalle.
- También muestra por fila el efecto promocional, el colchón de 8% y la variación
  del recomendado contra el mismo mes de 2025.

## 27. Gráficas temporales del backtest

- Se añadió una serie 2025 por SKU con venta real para modelar y los cinco
  pronósticos comparables.
- La línea de julio separa la prueba enero-junio de la prueba julio-diciembre.
- Se añadió una gráfica de error mensual con color para subestimación y
  sobreestimación.
- Es posible ocultar modelos y cambiar el modelo cuyo error se inspecciona.
- La prueba automática con todos los modelos, Protegido y sólo
  Empresa/Recomendado terminó sin excepciones.
