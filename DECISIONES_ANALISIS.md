# Bitácora de decisiones del análisis

Este documento registra qué se encontró, qué se decidió y por qué. Los datos
originales no se modificarán directamente: las correcciones se aplicarán sobre
una copia y cada tipo de inconsistencia se analizará por separado.

## Método para resolver inconsistencias

Para cada problema se seguirá este orden:

1. Detectarlo y contar cuántos casos existen.
2. Revisar ejemplos concretos.
3. Compararlo con las otras hojas cuando sea posible.
4. Decidir qué tratamiento aplicar y justificarlo.
5. Medir cómo cambia el resultado después del tratamiento.
6. Registrar la decisión en esta bitácora.

No se reemplazarán vacíos, negativos o valores extremos de manera automática.

## D01. Considerar estacionalidad

**Estado:** decisión confirmada.

**Decisión:** la evaluación incluirá métodos que tomen en cuenta el mes del año,
porque la demanda podría presentar patrones estacionales. Considerar
estacionalidad no significa asumir que existe: los modelos estacionales se
compararán contra alternativas simples mediante una prueba histórica.

**Alternativas previstas:**

- Nivel reciente.
- Mismo mes del año anterior.
- Promedio del mismo mes de los dos años anteriores.

**Validación pendiente:** comparar los errores de cada alternativa antes de
elegir el método final.

## D02. Nivel de segmentación del pronóstico

**Estado:** decisión preliminar, sujeta a la calidad y cantidad de datos.

**Decisión:** intentar construir el pronóstico mensual por SKU y región. Las
categorías se obtendrán sumando los SKU correspondientes y el resultado nacional
se obtendrá sumando las regiones.

**Razón:** este nivel permite reconocer diferencias regionales sin fragmentar
inicialmente la información hasta SKU, canal y región al mismo tiempo.

**Validaciones pendientes:**

- Confirmar que cada serie SKU-región tenga suficientes meses utilizables.
- Comparar su desempeño contra una alternativa menos segmentada.
- Evaluar canal en una etapa posterior.
- Para comparar con `Pronostico_Empresa`, sumar las regiones porque esa hoja no
  contiene región.

## D03. Homologar nombres de canal

**Estado:** decisión confirmada.

**Hallazgo:** un mismo canal aparece con nombres diferentes.

**Decisión:** usar estas equivalencias:

- `E-commerce` pasa a `Ecommerce`.
- `Super` pasa a `Supermercado`.
- `SUPERMERCADO` pasa a `Supermercado`.

**Razón:** son variantes evidentes de los mismos canales. Sólo se modifica la
etiqueta; no se alteran unidades, precios ni promociones.

`Ecommerce` y `Supermercado` permanecen como canales diferentes. Nunca se
convierte ni se suma uno dentro del otro. Después de retirar duplicados y
homologar únicamente las variantes de escritura quedaron 2,700 filas por cada
canal: Ecommerce, Mayorista y Supermercado.

## D04. Retirar duplicados exactos

**Estado:** decisión confirmada.

**Hallazgo:** se recibieron 8,114 filas cuando la combinación de 36 meses, 25
SKU, 3 canales y 3 regiones produce 8,100. Había 28 filas involucradas en
duplicados exactos, equivalentes a 14 copias adicionales.

**Decisión:** conservar una aparición de cada fila y retirar sus copias exactas
de la tabla de trabajo.

**Validación:** después del tratamiento quedan 8,100 filas y ninguna clave
`Fecha + SKU + Canal + Region` repetida.

## D05. Unidades vacías no equivalen automáticamente a cero

**Estado:** decisión confirmada y aplicada en la tabla para modelado.

**Hallazgo:** después de retirar duplicados existen 28 celdas vacías en
`Unidades` y 54 filas que contienen un cero escrito explícitamente. Son dos
representaciones distintas y no se asumirán equivalentes.

**Cruce entre hojas:**

- Los 28 vacíos afectan 27 combinaciones SKU-mes; una combinación tiene dos
  celdas vacías.
- En los 26 SKU-meses comparables, `Venta_Real` coincide con la suma de las
  unidades conocidas.
- Enero de 2023 no puede compararse porque `Pronostico vs Real` comienza en
  febrero de 2023.
- La otra hoja también omite los vacíos al sumar, por lo que no permite recuperar
  el valor original ni demostrar que fuera cero.

**Decisión aplicada:** la columna original `Unidades` se conserva sin cambios.
Para modelar se creó una columna separada, `Unidades_Modelo`, y una bandera
`Unidad_Fue_Estimada` que permita reconocer las 28 observaciones completadas.

Para cada vacío se estudiarán dos referencias del mismo SKU, canal y región:

- **Estimación temporal:** interpolar entre los valores conocidos que rodean el
  vacío. Si existen dos vacíos consecutivos, repartir gradualmente el cambio
  entre el último mes conocido y el siguiente mes conocido.
- **Estimación estacional:** promediar el mismo mes de todos los demás años
  disponibles, no solamente el año inmediatamente anterior o posterior.

Para un vacío al inicio o al final del historial, donde no existen dos extremos
para interpolar, se utilizará la estimación estacional. Si solamente existe un
año comparable, podrá utilizarse como respaldo, pero la observación se marcará
como una estimación con menor respaldo.

**Pruebas realizadas:** sobre 7,518 observaciones conocidas, el WAPE temporal fue
19.96%, el estacional 21.08% y la combinación de ambos 18.51%. Al separar las
filas sin promoción, el método combinado obtuvo el menor WAPE: 15.92%.

Para promociones se construyó una demanda base sin promociones y se calculó el
factor histórico de aumento por SKU. El factor mediano global fue 1.7446. En una
validación donde los factores se aprendieron con 2023-2024 y se probaron con 171
promociones de 2025, el WAPE bajó de 46.83% a 18.02%. En los SKU con vacíos
promocionales, el WAPE ajustado fue 11.43% para `SKU-1003`, 13.42% para
`SKU-1005` y 12.20% para `SKU-1008`.

**Regla final:** se utilizaron 23 estimaciones combinadas temporal-estacional, 3
estimaciones de base sin promoción multiplicada por el factor mediano del SKU y
2 estimaciones estacionales de respaldo para los extremos del historial. Las
promociones se consideran estimaciones con mayor incertidumbre porque no se
conocen su tipo, intensidad ni duración.

**Validación final:** `Unidades` conserva sus 28 vacíos, `Unidades_Modelo` tiene
cero vacíos y las 28 filas estimadas están marcadas. Las estimaciones agregan
21,372.19 unidades respecto de la suma que omitía los valores desconocidos.

**Excepción de ciclo de vida:** para `SKU-1021` no se usarán como referencia los
ceros registrados desde julio de 2025, porque corresponden a su periodo de
inactividad o pausa. Por ejemplo, el cero de octubre de 2025 no representa una
estimación válida para completar una observación anterior de octubre de 2024.

## D06. Convertir Fecha a un tipo temporal

**Estado:** decisión confirmada.

**Hallazgo:** las 8,100 filas contienen fechas válidas con formato `YYYY-MM`.
El periodo va de enero de 2023 a diciembre de 2025 y contiene 36 meses
distintos. No se detectaron fechas inválidas.

**Decisión:** convertir `Fecha` de texto a fecha antes de ordenar, agrupar o
construir las series mensuales.

**Razón:** los cálculos de orden, año, mes y desplazamientos temporales deben
hacerse con fechas y no con cadenas de texto.

## D07. Precios unitarios vacíos

**Estado:** decisión confirmada.

**Hallazgo:** existen 19 valores vacíos en `Precio_Unitario_USD`.

**Evidencia:** para las 19 filas se encontró un precio del mismo SKU, mes, región
y estado de promoción en otro canal. Cada grupo tenía un único precio y, en
todos los casos, ese valor coincidió exactamente con `Precio_Venta_USD` de la
hoja `Precios y Costos`. Ningún SKU quedó sin precio maestro y ninguna de las 19
filas correspondía a una promoción. Además, al revisar todos los precios
originales, cada uno de los 25 SKU conservó un único precio en todos los meses,
canales y regiones; los 25 coincidieron con el catálogo y no se detectó ningún
SKU con problemas de precio.

**Decisión:** completar los 19 valores vacíos con `Precio_Venta_USD` del catálogo
maestro. Conservar una marca que identifique las filas cuyo precio fue
completado.

**Razón:** se utilizan dos fuentes concordantes y no se reemplaza el dato con
cero, un promedio ni un valor arbitrario. El posible origen manual del vacío se
mantiene como hipótesis y no como hecho comprobado.

**Código utilizado para comprobar y aplicar la decisión:**

```python
# 1. Localizar las filas con precio vacío.
precios_vacios = ventas_limpias.loc[
    ventas_limpias["Precio_Unitario_USD"].isna(),
    [
        "Fecha",
        "SKU",
        "Producto",
        "Canal",
        "Region",
        "Precio_Unitario_USD",
        "Promocion",
    ],
]

# 2. Buscar precios del mismo SKU, mes y región en los otros canales.
referencias_precio = (
    ventas_limpias
    .dropna(subset=["Precio_Unitario_USD"])
    .groupby(["Fecha", "SKU", "Region"], as_index=False)
    .agg(
        precios_distintos=("Precio_Unitario_USD", "nunique"),
        precio_referencia=("Precio_Unitario_USD", "first"),
    )
)

comparacion_precios = precios_vacios.merge(
    referencias_precio,
    on=["Fecha", "SKU", "Region"],
    how="left",
)

# 3. Comparar la referencia contra el catálogo maestro.
precios_costos = pd.read_excel(
    ARCHIVO,
    sheet_name="Precios y Costos",
)

catalogo_precios = precios_costos[
    ["SKU", "Precio_Venta_USD"]
].rename(
    columns={"Precio_Venta_USD": "precio_maestro"}
)

comparacion_maestro = comparacion_precios.merge(
    catalogo_precios,
    on="SKU",
    how="left",
    validate="many_to_one",
)

comparacion_maestro["diferencia_maestro"] = (
    comparacion_maestro["precio_referencia"]
    - comparacion_maestro["precio_maestro"]
)

# 4. Conservar una marca y completar desde el catálogo.
precio_por_sku = catalogo_precios.set_index("SKU")["precio_maestro"]

ventas_limpias["Precio_Fue_Completado"] = (
    ventas_limpias["Precio_Unitario_USD"].isna()
)

ventas_limpias["Precio_Unitario_USD"] = (
    ventas_limpias["Precio_Unitario_USD"]
    .fillna(ventas_limpias["SKU"].map(precio_por_sku))
)
```

**Comprobaciones finales:** 19 precios completados y cero precios vacíos
restantes.

## D08. Interpretación provisional de Promocion

**Estado:** pendiente de confirmación por parte de la empresa.

**Interpretación de trabajo:** `Promocion = 0` se leerá provisionalmente como
“sin promoción” y `Promocion = 1` como “con alguna promoción”. Todavía no se
asumirá que el indicador cubre todo el mes ni que representa un descuento en el
precio.

**Relación con D07:** las 19 filas cuyo precio fue completado tienen
`Promocion = 0`. Esta observación reduce una posible complicación, pero la
decisión de completar los precios se sostiene principalmente en la coincidencia
entre ventas equivalentes y el catálogo maestro.

## D09. Unidades negativas

**Estado:** decisión confirmada con la información disponible.

**Hallazgo:** existen 9 filas con unidades negativas, agrupadas en 8
combinaciones SKU-mes. Una combinación contiene dos filas negativas.

**Evidencia:** se comparó la suma original contra `Venta_Real` y contra una suma
alternativa que trataba temporalmente los negativos como cero. En los 8
SKU-meses, `Venta_Real` coincidió exactamente con la segunda alternativa. La
diferencia total entre ambas formas de sumar es de 7,378 unidades.

**Decisión:** en la tabla limpia, sustituir las 9 unidades negativas por cero y
conservar una marca que identifique las filas corregidas. La tabla original no
se modifica.

**Razón:** una demanda negativa no es válida para el pronóstico y las hojas
agregadas proporcionadas por la empresa muestran que esos registros no fueron
restados de `Venta_Real`. No existe evidencia para convertirlos a valores
positivos. Si la empresa indicara que representan devoluciones, se revisarían en
una variable separada en lugar de mezclarlas con la demanda.

**Explicación sencilla:** supongamos que tres registros de venta contienen 10,
5 y -2 unidades. Si se suman literalmente, el resultado es 13. Sin embargo, si
el reporte consolidado indica 15, significa que para construir ese reporte el
-2 no fue restado: se comportó como cero. Tampoco debe convertirse en +2, porque
eso produciría 17 y no coincidiría con el reporte.

El mismo patrón apareció en los datos. Para `SKU-1005` en marzo de 2023, la suma
con -169 era 3,118, pero `Venta_Real` era 3,287. Al tratar -169 como cero, la suma
se convirtió exactamente en 3,287. Para `SKU-1018` en octubre de 2024, los dos
negativos sumaban -4,982; al no restarlos, el total pasó de 1,507 a 6,489, que
coincide exactamente con `Venta_Real`. Las ocho combinaciones afectadas siguieron
este patrón.

La tabla limpia conservará el valor recibido en `Unidades_Original`, marcará la
fila en `Unidades_Negativa_Corregida` y utilizará cero en `Unidades`. Los vacíos
permanecen como vacíos porque son un problema diferente y todavía no tienen una
decisión final.

**Validación después de aplicar la decisión:**

- 9 filas marcadas como corregidas.
- 0 unidades negativas restantes.
- 7,378 unidades de diferencia total respecto de la suma que restaba los
  negativos.
- 28 unidades vacías restantes, sin modificación.

## D10. Ceros consecutivos de SKU-1021

**Estado:** decisión de limpieza y supuesto de pronóstico confirmados.

**Hallazgo:** los 54 ceros originales no son casos aislados. Corresponden a las
9 combinaciones de canal y región de `SKU-1021` (Azúcar 1 kg) durante los seis
meses de julio a diciembre de 2025.

**Evidencia adicional:**

- De enero a junio de 2025 el SKU registra ventas mensuales entre 6,687 y 8,821
  unidades según las hojas consolidadas.
- En julio, `Pronostico_Empresa` era 8,196, pero la venta real fue cero.
- En julio había 15,399 unidades de stock inicial y final, y cero venta perdida;
  por tanto, el cero no se explica por falta de inventario en el consolidado.
- De agosto a diciembre, pronóstico, venta, stock y venta perdida aparecen en
  cero.
- `Dias_Cobertura` queda vacío cuando no existe venta con la cual calcular el
  ritmo de consumo.
- Dos filas de octubre están marcadas con promoción a pesar de registrar cero
  unidades.

**Decisión de limpieza:** conservar los 54 ceros tal como fueron registrados.
Las distintas hojas coinciden en que no hubo venta y no existe evidencia para
reemplazarlos por un promedio o por ventas históricas.

**Supuesto de trabajo para el pronóstico:** clasificar `SKU-1021` como “inactivo
o en pausa desde julio de 2025”, sin afirmar como hecho que fue descontinuado.
El pronóstico base de enero a junio de 2026 será cero. Se conservará un escenario
alternativo de reactivación calculado con su historial anterior, para que el
usuario pueda activarlo manualmente si se confirma su regreso.

**Evaluación del modelo:** el cambio de estado no puede anticiparse únicamente
con un modelo de demanda. Para evitar ocultar su efecto, se reportará el error
tanto para todos los SKU como para los productos considerados activos, mostrando
`SKU-1021` como una excepción de ciclo de vida y no como un dato eliminado.

**Observación para reconciliación posterior:** en enero de 2025 la venta limpia
desde el detalle es 6,055, mientras que las hojas consolidadas muestran 6,687.
La diferencia es 632 y coincide con una copia exacta retirada durante la
limpieza de duplicados. Esto indica que el consolidado histórico incorporó al
menos ese duplicado y deberá considerarse al comparar pronósticos.

## D11. Coherencia entre stock final y venta perdida

**Estado:** validación confirmada; no requiere limpieza.

**Hallazgo:** se comparó si `Stock_Final` era cero contra la existencia de una
`Venta_Perdida_Unid` positiva.

- 683 SKU-meses terminaron con stock positivo y sin venta perdida.
- 187 SKU-meses terminaron con stock cero y venta perdida positiva.
- No existe ningún caso con stock final positivo y venta perdida positiva.
- Existen 5 casos con stock final cero y venta perdida cero; son agosto a
  diciembre de 2025 para el SKU-1021, ya clasificado como inactivo o en pausa.

**Conclusión:** los ceros de stock y venta perdida siguen un patrón coherente con
quiebres de inventario. Se conservarán como información operativa y no se
tratarán como errores de captura.

**Validación de las fórmulas:** en las 875 filas de inventario se cumplen sin
diferencias las siguientes relaciones:

- `Stock_Final = max(Stock_Inicial - Venta_Real, 0)`
- `Venta_Perdida_Unid = max(Venta_Real - Stock_Inicial, 0)`

Por la lógica interna del archivo, `Venta_Real` representa la demanda total
observada y `Venta_Perdida_Unid` es la parte que no pudo atenderse. Por tanto, no
se sumará la venta perdida a la venta real. Las unidades atendidas se calcularán
como `Venta_Real - Venta_Perdida_Unid`.

**Nota para exposición:** en los productos activos se observa este patrón:

- Si quedó stock al final del mes, no se registró venta perdida.
- Si el stock llegó a cero, se registró venta perdida.

Esto sugiere que la columna `Venta_Perdida_Unid` representa demanda que no pudo
atenderse por falta de inventario. Debe presentarse como una interpretación
respaldada por los datos, no como la definición oficial de la empresa. La única
excepción son cinco meses del `SKU-1021`, clasificado como inactivo o en pausa:
tuvo stock cero y venta perdida cero.

## D12. Consistencia entre SKU, producto y categoría

**Estado:** validación confirmada; no requiere limpieza.

**Hallazgo:** se revisaron los 25 SKU y los 25 productos. Cada SKU corresponde a
un único nombre de producto y a una única categoría. La validación inversa
también fue consistente: ningún producto aparece asociado con varios SKU o con
varias categorías.

**Decisión:** conservar los valores del catálogo sin modificaciones. Las columnas
`SKU`, `Producto` y `Categoria` pueden utilizarse para agrupar y segmentar los
pronósticos.

## D13. Valor atípico de SKU-1001 en marzo de 2025

**Estado:** decisión confirmada y aplicada únicamente a la tabla para modelado.

**Hallazgo:** el método IQR marcó 292 observaciones extremas. De ellas, 250
corresponden a promociones y 42 a filas sin promoción. Casi todos los extremos
sin promoción están cerca de sus límites o corresponden a unidades negativas ya
tratadas. La excepción material es `SKU-1001`, canal `Supermercado`, región
`Norte`, marzo de 2025, con 13,380 unidades y sin promoción.

**Evidencia:** la misma serie registró 1,175 unidades en marzo de 2023, 1,764 en
marzo de 2024, 1,285 en febrero de 2025 y 1,909 en abril de 2025. La estimación
temporal del caso es 1,597 y la estacional 1,469.5; su promedio es 1,533.25. Al
usar este valor, el total mensual del SKU sería 9,806.25, cercano al pronóstico
de la empresa de 9,968 unidades.

Las hojas consolidadas muestran 21,653 unidades, pero no constituyen una
confirmación independiente: el valor se propagó desde el detalle. Inventario
utilizó ese mismo total para calcular 10,484 unidades perdidas contra 11,169 de
stock inicial.

**Decisión:** conservar 13,380 en `Unidades` como dato original y utilizar
1,533.25 en `Unidades_Modelo`. La fila se marca con
`Unidad_Fue_Ajustada_Atipico = True` y el método “Promedio temporal-estacional
validado”. No se afirma que el valor correcto fuera 1,380; se utiliza una
estimación reproducible para evitar que un probable error de captura distorsione
el pronóstico.

**Impacto:** el ajuste reduce 11,846.75 unidades. Combinado con las 21,372.19
unidades incorporadas al completar vacíos, el impacto neto de los tratamientos
es de 9,525.44 unidades respecto de la suma original que omitía los vacíos.

## D14. Claves y duplicados en las hojas maestras y consolidadas

**Estado:** validación confirmada; no requiere limpieza.

**Hallazgo:** `Pronostico vs Real` contiene 875 filas y 875 claves únicas
`Fecha + SKU`. `Inventario y Quiebres` también contiene 875 filas y 875 claves
únicas. Ambas hojas abarcan 35 meses y 25 SKU, y no existe ninguna combinación
presente en una hoja y ausente en la otra.

`Precios y Costos` contiene 25 filas y 25 SKU únicos. En las tres hojas se
encontraron cero claves repetidas y cero duplicados exactos.

**Decisión:** conservar las tres hojas sin eliminación de filas. Las claves se
consideran aptas para cruces uno a uno. `Resumen Gerencia` se revisará por
indicadores, porque no tiene la misma granularidad transaccional.

## D15. Reconciliación entre detalle, consolidado y tabla para modelado

**Estado:** validación confirmada.

**Hallazgo:** al agregar el detalle original por `Fecha + SKU`, conservando
duplicados, omitiendo vacíos y tratando negativos como cero, se obtienen
exactamente los mismos 7,305,668 registros de unidades que `Venta_Real` en los
875 SKU-meses. No existe ninguna diferencia entre `Venta_Sistema` y
`Venta_Real`.

Esto confirma que el consolidado se derivó del detalle original y explica por
qué también contiene sus duplicados y el valor atípico de marzo de 2025. No es
una fuente independiente para validar esos problemas.

La retirada de duplicados afectó 13 SKU-meses y redujo 10,936 unidades, dejando
7,294,732 unidades limpias antes de estimaciones. En los 35 meses cubiertos por
el consolidado, las estimaciones y el ajuste atípico incorporan un efecto neto
de 9,207.44 unidades. `Venta_Modelo` suma 7,303,939.44, es decir, 1,728.56
unidades menos que el consolidado original.

**Trazabilidad de los cambios:** 40 SKU-meses presentan alguna diferencia: 13
por limpieza de duplicados, 26 por estimaciones de vacíos y uno por el ajuste
atípico. El vacío de enero de 2023 no aparece en esta comparación porque las
hojas consolidadas comienzan en febrero de 2023.

**Decisión:** utilizar `Venta_Modelo` para el análisis y el pronóstico, conservar
`Venta_Real` como cifra histórica reportada por la empresa y mostrar por separado
las diferencias de limpieza. No se sobrescribirán los consolidados originales.

## D16. Reconciliación de inventario con demanda limpia

**Estado:** validación confirmada; se conserva un escenario original y otro
recalculado.

**Hallazgo:** `Venta_Real` coincide entre las hojas de pronóstico e inventario en
los 875 SKU-meses. Al aplicar las mismas fórmulas de inventario a `Venta_Modelo`,
los quiebres bajan de 187 a 185, la venta perdida de 201,617 a 190,050.05 y la
venta atendida aumenta de 7,104,051 a 7,113,889.39 unidades.

**Decisión:** no modificar el inventario reportado. Mantener columnas separadas
`Stock_Final_Modelo`, `Venta_Perdida_Modelo` y `Venta_Atendida_Modelo` para
mostrar cómo cambian los indicadores al usar demanda limpia. En marzo de 2025,
el ajuste de `SKU-1001` elimina un quiebre artificial de 10,484 unidades.

## D17. Días de cobertura y nivel de servicio

**Estado:** fórmula de cobertura confirmada; definición gerencial de servicio no
reproducible exactamente.

**Días de cobertura:** las 875 filas coinciden con
`Stock_Final / Venta_Real × 30`, redondeado a un decimal. Los seis vacíos ocurren
cuando `Venta_Real` es cero y la división no está definida.

**Nivel de servicio por unidades:** `Venta_Atendida / Venta_Real`. El historial
original obtiene 97.24% y el limpio 97.40%. Para 2025 los resultados son 97.02%
y 97.49%, respectivamente.

**Nivel de servicio por ciclos:** el porcentaje de SKU-meses sin venta perdida
es 78.63% en todo el historial y 79.67% en 2025.

**Conclusión:** ninguna de estas dos definiciones reproduce el 96% declarado. Se
presentará el nivel por unidades con su fórmula explícita y se mantendrá 96% como
cifra declarada cuya definición requiere confirmación.

## D18. Márgenes, costos y rotación

**Estado:** márgenes y validaciones confirmados; rotación declarada no
reproducible.

Los 25 márgenes están entre cero y uno, por lo que `Margen_Bruto_pct` representa
un porcentaje decimal. No existen precios, costos de almacenaje ni vidas útiles
no positivos. Como no se proporciona costo real del producto, se derivó
`Precio_Venta_USD × (1 - Margen_Bruto_pct)` únicamente como aproximación.

Para ventas atendidas de 2025 se obtienen USD 11,036,458.00 de ingreso,
USD 3,406,163.35 de margen bruto, 30.86% de margen ponderado y USD 276,466.30 de
costo anual estimado de almacenaje.

La rotación estándar aproximada, calculada como costo de venta atendida dividido
entre valor promedio del inventario, es 11.03 veces. No coincide con 5.1. El
archivo no contiene costo contable real, compras, recepciones ni la definición o
alcance de Gerencia, por lo que no se ajustará el cálculo para forzar la cifra.

## D19. Reconciliación del Resumen Gerencia

**Estado:** inconsistencia documentada; no se modifica el reporte original.

La venta total 2025 declarada es USD 12,344,981, mientras que las regiones
declaradas suman USD 11,398,874: existe una diferencia interna de USD 946,107.

El ingreso calculado desde el detalle original y precios maestros es
USD 11,399,329.07, muy cercano al desglose regional. La demanda limpia valuada
suma USD 11,345,787.06 y la venta atendida USD 11,036,458.00. Ninguna cifra
reproduce el total gerencial.

**Decisión:** mostrar por separado total declarado, suma regional, demanda
original, demanda limpia y venta atendida. No inferir qué integra los
USD 946,107 faltantes sin información adicional.

## D20. Alcance de la columna Promocion

**Estado:** efecto cuantificado; significado operativo incompleto.

La columna solo contiene 0 o 1. Fue posible medir su efecto histórico y utilizar
factores validados para completar tres vacíos, pero no se conocen tipo,
descuento, intensidad ni duración. Una promoción futura requerirá información de
un calendario de promociones o un ajuste manual. No se aplica un multiplicador futuro explícito,
aunque los efectos de promociones históricas permanecen dentro de los promedios.

## D21. Selección del modelo de pronóstico

**Estado:** modelo seleccionado mediante dos pruebas históricas de seis meses.

Se compararon último dato, promedio de tres meses, mismo mes del año anterior,
promedio estacional y combinación reciente-estacional. Al nivel `SKU + Región`,
el promedio estacional obtuvo WAPE de 15.17% y sesgo de -7.20%; el combinado
obtuvo WAPE de 15.37% y sesgo de -4.38%.

**Decisión:** utilizar el combinado porque pierde solamente 0.20 puntos de WAPE
y reduce la tendencia a quedarse corto. La fórmula es el promedio entre el nivel
de los últimos tres meses y el promedio histórico del mismo mes calendario.

El pronóstico empresarial de 2025 obtuvo WAPE de 19.22% y sesgo de +7.69% al
excluir el periodo de pausa de Azúcar. Agregado a SKU-mes, el combinado obtuvo
12.66% de WAPE en la prueba de 2025.

## D22. Escenarios de decisión

**Estado:** se separa estimación de demanda y tolerancia al riesgo.

**Pronóstico base:** resultado directo del modelo combinado.

**Escenario de protección:** base multiplicada por 1.0458, factor que corrige el
sesgo de -4.38% observado en el backtest. No se denomina inventario de seguridad
porque no existen tiempo de reposición, pedidos en tránsito ni caducidad por
lote.

El pronóstico base enero-junio de 2026 es 1,209,577.95 unidades; el escenario de
protección es 1,264,931.09. `SKU-1021` permanece en cero en ambos escenarios y
solo se reactivará mediante un ajuste manual explícito.

## D23. Promociones en el horizonte futuro

**Estado:** limitación explícita.

Como no existe calendario 2026, el escenario recomendado sólo infiere una
promoción cuando el mismo SKU y mes la presentó en al menos dos años. Se muestra
por separado la demanda base sin promoción, el recomendado con recurrencia y el
ajuste manual. Un calendario recibido debe sustituir esta inferencia.

## D24. Alcance del dashboard

**Estado:** versión narrativa funcional y validada.

El dashboard se organiza en seis pestañas: resumen; datos y limpieza; modelos
probados; pronóstico 2026; robustez; y notas para exponer. Documenta qué se
encontró, qué se decidió y por qué antes de mostrar métricas y escenarios.

En el pronóstico mantiene simultáneamente visibles base sin promoción,
recomendado y protegido 8%. Al cambiar de escenario actualiza el total, la
diferencia frente al recomendado, la gráfica histórica y el resultado
descargable. También permite filtrar, cambiar un porcentaje, sumar unidades o
excluir una selección.

Para una plantilla nueva se aplican reglas generales. Los valores atípicos y las
excepciones de negocio requieren revisión humana; no se codifican como reglas
universales los casos particulares encontrados en este archivo.

## D25. Nivel principal y desglose del pronóstico

**Estado:** decisión revisada antes de cerrar el modelo final.

La empresa entrega su pronóstico y administra el inventario al nivel mensual por
SKU. Por ello, el pronóstico principal también se calculará como `Fecha + SKU`.
Esto permite compararlo justamente con `Pronostico_Empresa` y utilizarlo para
planeación total, compras e inventario.

La región se conservará como desglose secundario. Después de pronosticar el total
del SKU, se distribuirá entre Norte, Centro y Sur mediante participaciones
históricas que podrán variar por mes. Se verificará siempre que la suma de las
tres regiones coincida exactamente con el total del SKU.

**Consecuencia:** la elección anterior del modelo combinado basada principalmente
en WAPE regional se considera provisional. Los modelos y las ponderaciones se
volverán a evaluar al nivel `Fecha + SKU` antes de generar la versión definitiva
de enero-junio de 2026.

## D26. Pesos, riesgo de subestimación y promociones

**Estado:** pesos seleccionados y validados; el calendario futuro continúa
pendiente.

Además de WAPE y sesgo, se separó el error en subestimación y sobreestimación.
Esta separación evita que ambos tipos de error se cancelen y responde mejor al
objetivo de reducir ventas perdidas.

Las promociones se normalizaron mediante factores por SKU entrenados con
2023-2024 y validados en 2025. El pronóstico base se calcula sin el aumento
promocional; cuando existe un calendario conocido, se aplica después un
multiplicador aproximado según la proporción de combinaciones canal-región en
campaña.

Se probaron pesos crecientes en pasos de 10%, usando enero-junio de 2025 para
seleccionar y julio-diciembre para validar sin cambios. Se eligió 0%-50%-50% —es
decir, el promedio de los dos meses comparables más recientes— para
los tres meses recientes. En ambas ventanas activas produjo WAPE 8.10%, sesgo
-2.44%, subestimación 5.27% y sobreestimación 2.83%.

**Decisión:** utilizar el promedio de los dos meses comparables más recientes
como configuración alternativa porque reduce el
riesgo de subestimar y mantiene el menor WAPE del grupo seleccionado. El WAPE de
8.10% presupone que se reciben las promociones futuras. Para 2026 se
mostrarán por separado un escenario base sin campaña y un escenario promocional
editable; no se inventará un calendario.

## D27. Pronóstico revisado enero-junio de 2026

**Estado:** generado, validado e incorporado al dashboard.

Se consideró recurrente una promoción solamente cuando el mismo SKU presentó
alguna campaña en ese mismo mes calendario durante al menos dos años distintos.
La proporción esperada es el promedio histórico de combinaciones canal-región
marcadas en promoción. Los eventos observados en un solo año no se proyectan.

Se detectaron 58 combinaciones SKU-mes recurrentes. Dos pertenecen a `SKU-1021`;
la regla de pausa tiene prioridad y deja 56 promociones recurrentes activas.

- Total base sin promociones: 1,192,504.69 unidades.
- Total recomendado con recurrencia: 1,224,820.00 unidades.
- Diferencia atribuida a recurrencia: 32,315.31 unidades.
- Filas principales: 150, correspondientes a 25 SKU por seis meses.

El recomendado se distribuyó entre las tres regiones mediante la participación
histórica del mismo SKU y mes calendario. Se generaron 450 filas regionales. Las
participaciones suman entre 0.9999999999999999 y 1.0; la máxima diferencia entre
la suma regional y el total SKU es menor a 0.000000000004 unidades.

**Decisión:** usar `Pronostico_Recomendado` como escenario de trabajo bajo la
hipótesis de recurrencia histórica, manteniendo visibles `Pronostico_Modelo_Sin_Promocion`,
el multiplicador y los ajustes manuales. Esta regla no sustituye un calendario
de promociones recibido.

La misma regla de recurrencia se probó retrospectivamente, usando en cada corte
solamente la información que habría estado disponible en ese momento. En las dos
ventanas activas de 2025 obtuvo WAPE 10.56%, sesgo -5.35%, subestimación 7.96% y
sobreestimación 2.61%. Por tanto, 10.56% es la validación realista que corresponde
al escenario recomendado actual. El WAPE 8.10% de D26 representa el escenario
ideal en el que se recibe anticipadamente el calendario de promociones.

## D28. Escenario protegido contra subestimación

**Estado:** probado y generado como escenario separado.

Se probaron protecciones de 0%, 2%, 4%, 6%, 8% y 10%. El porcentaje se eligió
solamente con enero-junio de 2025, buscando el sesgo más cercano a cero; después
se conservó sin cambios para validar julio-diciembre. La primera ventana eligió
8%: su sesgo cambió de -7.82% a -0.45% y su WAPE de 11.68% a 10.50%.

En la segunda ventana, el mismo 8% produjo WAPE 10.72% y sesgo +4.91%. Al unir
ambas ventanas, el escenario protegido obtuvo WAPE 10.61%, sesgo +2.22%,
subestimación 4.19% y sobreestimación 6.42%. Frente al recomendado sin colchón,
reduce la subestimación de 7.96% a 4.19%, pero aumenta la sobreestimación de
2.61% a 6.42% y el WAPE apenas sube de 10.56% a 10.61%.

**Decisión:** conservar `Pronostico_Recomendado` como estimación central y mostrar
`Pronostico_Protegido` como alternativa explícita para una política que priorice
evitar faltantes. No se incorpora automáticamente a `Pronostico_Final`, porque
usar el colchón es una decisión de riesgo e inventario, no una corrección cierta
de la demanda.

Para enero-junio de 2026, el recomendado suma 1,224,820.00 unidades y el protegido
con 8% suma 1,322,805.60 unidades.

## D29. Robustez por SKU, categoría y mes

**Estado:** calculada, exportada y visible en el dashboard.

El 8% se evaluó por segmento para comprobar que el resultado global no ocultara
fallas particulares. Reduce la subestimación en los 25 SKU, pero sólo mejora el
WAPE en 13. Por categoría, mejora el WAPE de Galletas de 12.40% a 10.88% y
ligeramente el de Despensa de 9.82% a 9.80%; en Bebidas y Lácteos reduce la
subestimación, pero no mejora la precisión total.

**Decisión:** el dashboard debe permitir alternar entre SKU, categoría y mes,
mostrar el WAPE recomendado y protegido, y señalar visualmente cuándo el 8%
mejora o empeora WAPE. Esto refuerza que el protegido es una política de riesgo,
no un modelo universalmente más exacto.

## D30. Trazabilidad por SKU y mes

**Estado:** generada e incorporada al dashboard.

La evaluación global se complementa con 294 comparaciones SKU-mes de 2025. Para
cada una se muestran la venta limpia usada para modelar, los pronósticos de la
empresa, mismo mes anterior, ponderado estacional, recomendado y protegido, así
como error en unidades y porcentaje.

También se generaron 150 filas de trazabilidad 2026 con la venta del mismo mes en
2023, 2024 y 2025, la base sin promoción, el recomendado, el protegido, el efecto
promocional y la variación contra 2025.

**Decisión:** estas tablas sirven para explicar un caso concreto, pero no para
elegir el modelo mirando solamente un mes. La selección sigue basada en el
backtest completo.

## D31. Ajuste temporal visible por modelo

**Estado:** incorporado al dashboard.

Además de los KPI acumulados, cada SKU puede revisarse como serie mensual de
2025. La gráfica superpone la venta limpia usada para modelar con empresa, mismo
mes anterior, ponderado estacional, recomendado y protegido. Una segunda gráfica
muestra el error firmado de un modelo seleccionado: negativo cuando subestima y
positivo cuando sobreestima.

**Decisión:** mantener visibles las dos ventanas del backtest y separarlas en
julio. Esto permite detectar modelos que obtienen buen WAPE total, pero siguen
mal la forma mensual o fallan en picos específicos.

## D32. Explicar cada término y fórmula en la entrega

**Decisión:** el dashboard y la guía deben explicar los indicadores antes de
utilizarlos. En particular, WAPE se presentará como unidades de error absoluto
por cada 100 unidades reales y no como “porcentaje de precisión”. También se
mostrarán la fórmula e interpretación del sesgo, subestimación, sobreestimación,
días de cobertura, nivel de servicio, margen, rotación y cada paso del modelo.

**Motivo:** la entrega debe poder comprenderse y defenderse sin depender de
jerga técnica ni de una explicación externa.

## D33. Traducir el pronóstico filtrado a una conclusión verbal

**Decisión:** la pestaña de pronóstico construirá una frase dinámica con el
modelo, categoría o SKU, canal, región, mes y unidades seleccionadas. También mostrará
el valor antes del ajuste manual, el resultado mostrado y la diferencia causada
por el cambio.

**Motivo:** un gerente debe poder leer directamente qué se proyecta sin tener
que interpretar primero una tabla. La frase también facilita responder en vivo
cuando se pide modificar un producto, región o porcentaje.

## D34. Evitar información futura en el factor promocional

**Hallazgo:** aunque las filas usadas para estimar el factor promocional eran de
2023-2024, su referencia estacional se había calculado inicialmente sobre todo
el historial y podía incorporar 2025 de manera indirecta.

**Decisión:** recalcular tanto las filas promocionales como sus referencias
temporal y estacional usando exclusivamente datos disponibles hasta diciembre
de 2024. Después se regeneraron el backtest, los archivos y el dashboard.

**Resultado:** el WAPE realista cambió de 10.50% a 10.56%. La diferencia es
pequeña, pero la segunda cifra es metodológicamente correcta porque no mira el
futuro. El pronóstico recomendado enero-junio de 2026 quedó en 1,224,820.00
unidades.

## D35. Admitir archivos nuevos y ajustes manuales

**Decisión:** el dashboard acepta otro Excel con las mismas columnas mínimas,
valida fechas, promociones, claves y catálogo, aplica la limpieza y proyecta
los seis meses inmediatamente posteriores al último dato recibido. También reserva
automáticamente los últimos seis meses del archivo para calcular un WAPE y sesgo
propios, siempre que exista historia suficiente.

Las correcciones explícitas del nuevo archivo tienen prioridad: si llegan las
unidades, precios o negativos corregidos, se utilizan esos valores y dejan de
aplicarse las estimaciones anteriores. Un cambio en el significado o formato de
`Promocion` no se interpreta automáticamente; el programa se detiene para pedir
una regla de conversión.

Se añadió un desglose reconciliado por `Canal + Región`. El modelo principal
continúa calculándose por SKU-mes y después se reparte usando participaciones
históricas; las nueve combinaciones regresan exactamente al total del SKU. Esto
permite subir Ecommerce, Mayorista o Supermercado sin afirmar que los canales
son equivalentes.

Los ajustes pueden aplicarse a un mes o a los seis meses filtrados. La promoción
confirmada puede reemplazar la inferencia mediante el factor histórico del SKU o
un porcentaje manual; también puede descartarse una promoción inferida o
excluirse un producto. Siempre se muestran el valor previo, el nuevo y la
diferencia.

**Pruebas:** se cargó una copia con historia hasta diciembre de 2026 y
correcciones explícitas. El dashboard generó enero-junio de 2027, reportó cero
vacíos, negativos y precios faltantes, y recalculó su propio backtest. También se
probó un aumento de 10% sólo para Ecommerce en enero y la exclusión de un SKU en
los seis meses.

## D36. Reactivar Azúcar u otro SKU pausado cuando entreguen sus datos

**Decisión:** una pausa observada no se tratará como una característica
permanente del producto. Si un Excel nuevo trae ventas positivas recientes de
Azúcar, el modelo deja de marcarlo como pausado y utiliza automáticamente esos
datos. Si durante una sesión entregan directamente las seis demandas futuras,
el dashboard permite capturarlas en una tabla mensual como contingencia; la vía
preferida es cargar el Excel completo.

Los valores informados tienen prioridad sobre el pronóstico estadístico. En la
tabla representan el total mensual del SKU dentro de los filtros elegidos; el
programa sólo los reparte entre canal y región conforme a las participaciones
históricas para conservar el desglose. No se afirma haber pronosticado esos
valores: su origen queda identificado como `Reactivado manualmente`.

**Motivo:** los ceros de julio a diciembre de 2025 permitían inferir una pausa,
pero no una descontinuación definitiva. Si la empresa proporciona información
nueva, ésta debe reemplazar esa suposición.

## D37. Recalcular desde el Excel y separar demanda de economía

**Decisión:** agregar un modo local de actualización que vuelve a leer
`Datos_NutriVida.xlsx` y ejecuta de nuevo limpieza, backtest y pronóstico. De
esta manera, cambiar las unidades, completar vacíos, corregir negativos o
reactivar Azúcar en el Excel sí modifica el modelo y no sólo la visualización.

Las unidades y promociones alimentan el pronóstico de demanda. Precio y margen
alimentan la traducción financiera, pero no cambian las unidades porque no
existen datos suficientes para estimar elasticidad de precio. El costo del
producto se aproxima como `precio × (1 - margen bruto)`. Almacenaje y vida útil
se conservan como datos unitarios: calcular costo total o merma requeriría un
plan de inventario futuro y antigüedad de lotes.

También se separaron dos reconciliaciones. La primera compara el Excel capturado
contra las hojas consolidadas y descubre ediciones incompletas. La segunda
compara los datos ya limpios y permite mostrar el efecto deliberado de retirar
duplicados. Se vuelven a validar las fórmulas de stock final, venta perdida y
días de cobertura.

**Pruebas:** se modificaron copias en memoria del Excel y se reejecutó el modelo
completo. Cambiar unidades recientes alteró el pronóstico; corregir vacíos y
negativos redujo sus contadores; entregar los 54 registros recientes de Azúcar
lo reactivó; cambiar precio y margen modificó ingreso y costo sin alterar las
unidades. Las comprobaciones se conservaron en la documentación interna.

## D38. El Excel completo es la vía principal de actualización

**Decisión:** priorizar la carga de otro libro completo sobre la captura manual
de cifras futuras. El archivo puede traer hojas y columnas adicionales, pero
debe conservar las columnas mínimas utilizadas de `Ventas Historicas` y
`Precios y Costos`. Las hojas consolidadas son opcionales para pronosticar; si
aparecen, se aprovechan para reconciliar.

Se homologan espacios y mayúsculas de los canales y regiones conocidos sin
mezclar canales diferentes. También se rechazan identificadores vacíos, SKU
asociados a varios productos o categorías, claves repetidas no idénticas,
promociones distintas de 0/1 y datos financieros fuera de rango.

**Prueba:** se construyó una copia completa con 10,800 filas, correcciones
explícitas, una columna adicional e historia hasta diciembre de 2026. El sistema
generó enero-junio de 2027 con WAPE automático de 8.04%, sin vacíos, negativos,
claves duplicadas ni pronósticos inválidos.

## D39. El horizonte se mueve con la última fecha disponible

**Decisión:** el periodo dinámico no queda fijado a enero-junio. Comienza el mes
inmediatamente posterior al último dato y conserva una longitud de seis meses.
Por lo tanto, diciembre conduce a enero-junio del año siguiente, mientras que
junio conduce a julio-diciembre del mismo año.

**Prueba:** al cargar únicamente la historia hasta junio de 2025, el sistema
generó julio-diciembre de 2025. Produjo 1,350 filas de SKU, canal y región, sin
claves repetidas, vacíos ni valores negativos; su backtest automático obtuvo
WAPE 11.70% y sesgo -7.83%.

## D40. Admitir canales y regiones nuevos sin confundirlos con los existentes

**Decisión:** un nombre de canal o región que no pertenezca a las equivalencias
conocidas se conserva como una categoría nueva. Por ejemplo, `Conveniencia` no
se convierte en Ecommerce, Mayorista ni Supermercado, y `Oeste` no se convierte
en Norte, Centro ni Sur.

El modelo principal continúa calculando el total por SKU y mes. Para repartir
ese total entre canal y región se utiliza primero la participación histórica de
la combinación en el mismo mes calendario. Si el canal o la región son tan
nuevos que todavía no tienen ese mes en su historia, se utiliza como respaldo
su participación histórica general dentro del SKU. Después se normalizan todas
las participaciones para que sumen exactamente 100% y no se altere el total del
SKU.

Un canal o región sin ninguna venta histórica no tiene una participación que el
modelo pueda aprender. En ese caso se necesitaría una asignación explícita; no
sería responsable inventarla.

**Prueba:** se agregó `Conveniencia` y la región `Oeste` con datos únicamente de
enero a junio de 2025. Al proyectar julio-diciembre de 2025, el sistema conservó
ambos valores, generó seis resultados para la combinación, aplicó el respaldo
general, produjo cero pronósticos vacíos o negativos y mantuvo las
participaciones en 100% para cada SKU-mes.

## Definiciones pendientes de confirmación

- Significado operativo de `Promocion` y si representa todo el mes.
- Fórmula y alcance oficiales del 96% de servicio y la rotación de 5.1.
- Componentes incluidos en la venta total gerencial que no están en las regiones.
