"""Cálculos del modelo de demanda.

Aquí se encuentran la agregación histórica, el efecto promocional, la
estacionalidad, el promedio reciente, el pronóstico de seis meses y el reparto por
canal y región. Este módulo no dibuja gráficas ni conoce Streamlit.
"""

import pandas as pd


def construir_demanda_region(ventas):
    """Agrega ventas mensuales a SKU, canal y región."""
    return (
        ventas.groupby(
            [
                "Fecha", "SKU", "Producto", "Categoria", "Canal", "Region",
            ],
            as_index=False,
        )
        .agg(Demanda=("Unidades_Modelo", "sum"))
        .sort_values(["SKU", "Region", "Fecha"])
    )


def pronostico_preliminar(
    demanda, ventas, meses=6, fechas_objetivo=None
):
    """Aplica el método final a un archivo nuevo; falta validar su error."""
    claves_sku = ["SKU", "Producto", "Categoria"]
    claves_detalle = claves_sku + ["Canal", "Region"]
    cobertura_meses = (
        demanda.assign(Mes_Calendario=demanda["Fecha"].dt.month)
        .groupby("SKU")["Mes_Calendario"]
        .nunique()
    )
    sku_sin_ciclo_anual = cobertura_meses.loc[
        cobertura_meses.lt(12)
    ].index.tolist()
    if sku_sin_ciclo_anual:
        raise ValueError(
            "Para calcular estacionalidad, cada SKU necesita al menos una "
            "observación en los 12 meses del año. Falta cobertura para: "
            + ", ".join(map(str, sku_sin_ciclo_anual))
        )
    ultima = demanda["Fecha"].max()
    if fechas_objetivo is None:
        valores_fecha = pd.date_range(
            ultima + pd.offsets.MonthBegin(1), periods=meses, freq="MS"
        )
    else:
        valores_fecha = pd.to_datetime(fechas_objetivo)
    fechas = pd.DataFrame({"Fecha": valores_fecha})

    # 1. Estimar el efecto promocional contra una referencia temporal y otra
    # estacional del mismo SKU-canal-región.
    promociones = ventas.sort_values(claves_detalle + ["Fecha"]).copy()
    promociones["Mes_Calendario"] = promociones["Fecha"].dt.month
    promociones["Anio"] = promociones["Fecha"].dt.year
    promociones["Unidades_Sin_Promocion"] = promociones[
        "Unidades_Modelo"
    ].where(promociones["Promocion"].eq(0))
    promociones["Base_Temporal"] = (
        promociones.groupby(claves_detalle)["Unidades_Sin_Promocion"]
        .transform(
            lambda serie: serie.interpolate(
                method="linear", limit_area="inside"
            )
        )
    )
    promociones["Base_Estacional"] = (
        promociones.groupby(claves_detalle + ["Mes_Calendario"])[
            "Unidades_Sin_Promocion"
        ].transform("mean")
    )
    promociones["Base_Sin_Promocion"] = promociones[
        ["Base_Temporal", "Base_Estacional"]
    ].mean(axis=1)
    filas_promocionales = promociones.loc[
        promociones["Promocion"].eq(1)
        & promociones["Unidades_Modelo"].notna()
        & promociones["Base_Sin_Promocion"].gt(0)
    ].copy()
    filas_promocionales["Factor_Promocion"] = (
        filas_promocionales["Unidades_Modelo"]
        / filas_promocionales["Base_Sin_Promocion"]
    )
    factores = (
        filas_promocionales.groupby("SKU")["Factor_Promocion"].median()
        .clip(lower=1.0, upper=3.0)
    )
    factor_global = (
        filas_promocionales["Factor_Promocion"].median()
        if len(filas_promocionales)
        else 1.0
    )
    factor_global = min(max(float(factor_global), 1.0), 3.0)
    promociones["Factor_Promocional_SKU"] = (
        promociones["SKU"].map(factores).fillna(factor_global)
    )
    promociones["Unidades_Base"] = promociones["Unidades_Modelo"].where(
        promociones["Promocion"].eq(0),
        promociones["Unidades_Modelo"]
        / promociones["Factor_Promocional_SKU"],
    )

    # 2. Pronosticar primero por SKU, igual que el método elegido.
    demanda_sku = (
        promociones.groupby(["Fecha"] + claves_sku, as_index=False)
        .agg(Demanda=("Unidades_Base", "sum"))
    )
    ultimo_anio_completo = (
        ultima.year if ultima.month == 12 else ultima.year - 1
    )
    historial_estacional = demanda_sku.loc[
        demanda_sku["Fecha"].dt.year.le(ultimo_anio_completo)
    ].copy()
    historial_estacional["Mes_Calendario"] = (
        historial_estacional["Fecha"].dt.month
    )
    promedio_general = (
        historial_estacional.groupby(claves_sku, as_index=False)
        .agg(Promedio_General=("Demanda", "mean"))
    )
    indices = (
        historial_estacional
        .groupby(claves_sku + ["Mes_Calendario"], as_index=False)
        .agg(Promedio_Mes=("Demanda", "mean"))
        .merge(promedio_general, on=claves_sku, how="left")
    )
    indices["Indice_Estacional"] = (
        indices["Promedio_Mes"] / indices["Promedio_General"]
    )
    recientes = (
        demanda_sku.sort_values("Fecha")
        .groupby(claves_sku, group_keys=False)
        .tail(2)
        .copy()
    )
    recientes["Mes_Calendario"] = recientes["Fecha"].dt.month
    recientes = recientes.merge(
        indices[claves_sku + ["Mes_Calendario", "Indice_Estacional"]],
        on=claves_sku + ["Mes_Calendario"],
        how="left",
    ).sort_values(claves_sku + ["Fecha"])
    # La búsqueda de pesos probó tres meses y eligió 0%-50%-50%. Eso equivale
    # exactamente a promediar sólo los dos meses comparables más recientes.
    recientes["Peso"] = 0.5
    recientes["Nivel_Ponderado"] = (
        recientes["Demanda"] / recientes["Indice_Estacional"]
        * recientes["Peso"]
    )
    nivel = (
        recientes.groupby(claves_sku, as_index=False)
        .agg(
            Nivel_Suma=("Nivel_Ponderado", "sum"),
            Suma_Pesos=("Peso", "sum"),
        )
    )
    nivel["Nivel_Actual"] = nivel["Nivel_Suma"] / nivel[
        "Suma_Pesos"
    ].replace(0, pd.NA)
    futuro_sku = demanda_sku[claves_sku].drop_duplicates().merge(
        fechas, how="cross"
    )
    futuro_sku["Mes_Calendario"] = futuro_sku["Fecha"].dt.month
    futuro_sku = (
        futuro_sku.merge(
            nivel[claves_sku + ["Nivel_Actual"]],
            on=claves_sku,
            how="left",
        )
        .merge(
            indices[
                claves_sku + ["Mes_Calendario", "Indice_Estacional"]
            ],
            on=claves_sku + ["Mes_Calendario"],
            how="left",
        )
    )
    futuro_sku["Pronostico_Base"] = (
        futuro_sku["Nivel_Actual"] * futuro_sku["Indice_Estacional"]
    ).clip(lower=0)
    futuro_sku["Factor_Promocional_SKU"] = (
        futuro_sku["SKU"].map(factores).fillna(factor_global)
    )

    # 3. Aplicar sólo promociones recurrentes, sin inventar un calendario.
    anios_promocion = (
        promociones.loc[promociones["Promocion"].eq(1)]
        .groupby(["SKU", "Mes_Calendario"], as_index=False)
        .agg(Anios_Con_Promocion=("Anio", "nunique"))
    )
    proporcion = (
        promociones.groupby(["SKU", "Mes_Calendario"], as_index=False)
        .agg(Proporcion_Historica=("Promocion", "mean"))
        .merge(
            anios_promocion,
            on=["SKU", "Mes_Calendario"],
            how="left",
        )
    )
    proporcion["Anios_Con_Promocion"] = (
        proporcion["Anios_Con_Promocion"].fillna(0)
    )
    proporcion["Proporcion_Promocion_Esperada"] = (
        proporcion["Proporcion_Historica"].where(
            proporcion["Anios_Con_Promocion"].ge(2), 0.0
        )
    )
    futuro_sku = futuro_sku.merge(
        proporcion[
            ["SKU", "Mes_Calendario", "Proporcion_Promocion_Esperada"]
        ],
        on=["SKU", "Mes_Calendario"],
        how="left",
    )
    futuro_sku["Proporcion_Promocion_Esperada"] = futuro_sku[
        "Proporcion_Promocion_Esperada"
    ].fillna(0.0)
    futuro_sku["Pronostico_Recomendado"] = futuro_sku[
        "Pronostico_Base"
    ] * (
        1
        + futuro_sku["Proporcion_Promocion_Esperada"]
        * (futuro_sku["Factor_Promocional_SKU"] - 1)
    )
    futuro_sku["Pronostico_Protegido"] = (
        futuro_sku["Pronostico_Recomendado"] * 1.08
    )
    futuro_sku["Estado_SKU"] = "Activo"

    # 4. Marcar pausas explícitas observadas en los seis meses más recientes.
    demanda_sku_mes = (
        demanda.groupby(["Fecha", "SKU"], as_index=False)
        .agg(Demanda=("Demanda", "sum"))
    )
    ultimas_fechas = sorted(demanda_sku_mes["Fecha"].unique())[-6:]
    pausa = (
        demanda_sku_mes.loc[demanda_sku_mes["Fecha"].isin(ultimas_fechas)]
        .groupby("SKU")["Demanda"]
        .agg(lambda serie: len(serie) == len(ultimas_fechas) and serie.eq(0).all())
    )
    skus_pausados = pausa.loc[pausa].index
    mascara_pausa = futuro_sku["SKU"].isin(skus_pausados)
    futuro_sku.loc[mascara_pausa, "Estado_SKU"] = "Pausado"
    futuro_sku.loc[
        mascara_pausa,
        ["Pronostico_Base", "Pronostico_Recomendado", "Pronostico_Protegido"],
    ] = 0.0

    # 5. Repartir el total SKU entre Canal + Región sin cambiar el total.
    reparto = demanda.copy()
    reparto["Mes_Calendario"] = reparto["Fecha"].dt.month
    participaciones = (
        reparto.groupby(
            claves_detalle + ["Mes_Calendario"], as_index=False
        )
        .agg(Demanda_Historica=("Demanda", "sum"))
    )
    participaciones["Total_SKU_Mes"] = (
        participaciones.groupby(claves_sku + ["Mes_Calendario"])[
            "Demanda_Historica"
        ].transform("sum")
    )
    participaciones["Participacion_Canal_Region"] = (
        participaciones["Demanda_Historica"]
        / participaciones["Total_SKU_Mes"]
    )
    participaciones_generales = (
        reparto.groupby(claves_detalle, as_index=False)
        .agg(Demanda_Historica_General=("Demanda", "sum"))
    )
    participaciones_generales["Total_SKU_General"] = (
        participaciones_generales.groupby(claves_sku)[
            "Demanda_Historica_General"
        ].transform("sum")
    )
    participaciones_generales["Participacion_General"] = (
        participaciones_generales["Demanda_Historica_General"]
        / participaciones_generales["Total_SKU_General"]
    )
    combinaciones_observadas = reparto[claves_detalle].drop_duplicates()
    futuro = (
        futuro_sku.merge(
            combinaciones_observadas,
            on=claves_sku,
            how="left",
            validate="many_to_many",
        )
        .merge(
            participaciones[
                claves_detalle
                + ["Mes_Calendario", "Participacion_Canal_Region"]
            ],
            on=claves_detalle + ["Mes_Calendario"],
            how="left",
            validate="many_to_one",
        )
        .merge(
            participaciones_generales[
                claves_detalle + ["Participacion_General"]
            ],
            on=claves_detalle,
            how="left",
            validate="many_to_one",
        )
    )
    usa_respaldo_reparto = futuro["Participacion_Canal_Region"].isna()
    futuro["Metodo_Reparto"] = "Participación histórica del mismo mes"
    futuro.loc[usa_respaldo_reparto, "Metodo_Reparto"] = (
        "Participación histórica general del SKU"
    )
    futuro["Participacion_Canal_Region"] = futuro[
        "Participacion_Canal_Region"
    ].fillna(futuro["Participacion_General"])
    claves_total_futuro = claves_sku + ["Fecha"]
    suma_participaciones = futuro.groupby(claves_total_futuro)[
        "Participacion_Canal_Region"
    ].transform("sum")
    cantidad_combinaciones = futuro.groupby(claves_total_futuro)[
        "Participacion_Canal_Region"
    ].transform("size")
    futuro["Participacion_Canal_Region"] = (
        futuro["Participacion_Canal_Region"] / suma_participaciones
    ).where(
        suma_participaciones.gt(0),
        1 / cantidad_combinaciones,
    )
    for columna in [
        "Pronostico_Base",
        "Pronostico_Recomendado",
        "Pronostico_Protegido",
    ]:
        futuro[columna] *= futuro["Participacion_Canal_Region"]
    if futuro[
        ["Pronostico_Base", "Pronostico_Recomendado", "Pronostico_Protegido"]
    ].isna().any().any():
        raise ValueError(
            "El archivo no tiene historia suficiente para calcular algún "
            "índice estacional o reparto por canal-región."
        )
    return futuro


def promedio_ponderado(tabla, columna):
    """Pondera una métrica por demanda real."""
    total = tabla["Demanda_Real"].sum()
    return (tabla[columna] * tabla["Demanda_Real"]).sum() / total
