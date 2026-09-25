"""Orquestación completa: cargar, limpiar, validar, modelar y evaluar.

Este archivo conecta la limpieza con el modelo. Debes abrirlo si quieres cambiar
el orden del proceso, el periodo reservado para la validación histórica o las
hojas precalculadas del caso original.
"""

import pandas as pd

from limpieza_datos import (
    abrir_excel,
    auditar_reconciliacion_ventas,
    enriquecer_pronostico_financiero,
    limpiar_tablas_nuevas,
    validar_plantilla,
)
from modelo_demanda import construir_demanda_region, pronostico_preliminar


def ejecutar_flujo_analisis(
    origen_bytes, archivo_original, archivo_pronostico
):
    """Carga el caso validado o prepara provisionalmente un archivo nuevo."""
    if origen_bytes is None:
        libro_original = abrir_excel(archivo_original)
        ventas_originales = pd.read_excel(
            libro_original, sheet_name="Ventas Historicas"
        )
        catalogo = pd.read_excel(
            libro_original, sheet_name="Precios y Costos"
        )
        libro = abrir_excel(archivo_pronostico)
        demanda = pd.read_excel(
            libro, sheet_name="Historico Canal Region"
        ).rename(
            columns={"Demanda_Canal_Region": "Demanda"}
        )
        futuro = pd.read_excel(
            libro, sheet_name="Desglose Canal Region"
        ).rename(
            columns={
                "Pronostico_Recomendado_Detalle": "Pronostico_Recomendado",
                "Pronostico_Protegido_Detalle": "Pronostico_Protegido",
                "Pronostico_Final_Detalle": "Pronostico_Final",
            }
        )
        robustez = {
            "SKU": pd.read_excel(libro, sheet_name="Robustez SKU"),
            "Categoría": pd.read_excel(
                libro, sheet_name="Robustez Categoria"
            ),
            "Mes": pd.read_excel(libro, sheet_name="Robustez Mes"),
        }
        detalle_modelos = {
            "Validación 2025": pd.read_excel(
                libro, sheet_name="Detalle Validacion"
            ),
            "Pronóstico 2026": pd.read_excel(
                libro, sheet_name="Trazabilidad 2026"
            ),
        }
        diagnostico = {
            "filas_originales": 8114,
            "duplicados_retirados": 14,
            "unidades_vacias": 28,
            "unidades_negativas": 9,
            "precios_vacios": 19,
            "atipicos_altos_ajustados": 1,
            "filas_limpias": 8100,
        }
        es_caso_validado = True
    else:
        errores, libro = validar_plantilla(origen_bytes)
        if errores:
            raise ValueError(" | ".join(errores))
        ventas_crudas = pd.read_excel(libro, sheet_name="Ventas Historicas")
        catalogo = pd.read_excel(libro, sheet_name="Precios y Costos")
        ventas_originales, diagnostico = limpiar_tablas_nuevas(
            ventas_crudas, catalogo
        )
        diagnostico.update(
            auditar_reconciliacion_ventas(
                ventas_originales, libro, ventas_crudas
            )
        )
        demanda = construir_demanda_region(ventas_originales)
        futuro = pronostico_preliminar(demanda, ventas_originales)

        # Backtest automático del archivo nuevo: reservamos sus últimos seis
        # meses y los pronosticamos usando sólo la historia anterior.
        fechas_historia = sorted(demanda["Fecha"].unique())
        diagnostico["backtest_disponible"] = False
        if len(fechas_historia) >= 18:
            fechas_prueba = fechas_historia[-6:]
            inicio_prueba = pd.Timestamp(fechas_prueba[0])
            fechas_crudas = pd.to_datetime(
                ventas_crudas["Fecha"], errors="coerce"
            )
            ventas_entrenamiento, _ = limpiar_tablas_nuevas(
                ventas_crudas.loc[fechas_crudas.lt(inicio_prueba)].copy(),
                catalogo,
            )
            demanda_entrenamiento = construir_demanda_region(
                ventas_entrenamiento
            )
            pronostico_prueba = pronostico_preliminar(
                demanda_entrenamiento,
                ventas_entrenamiento,
                fechas_objetivo=fechas_prueba,
            )
            prueba_predicha = (
                pronostico_prueba
                .groupby(
                    ["Fecha", "SKU", "Producto", "Categoria"],
                    as_index=False,
                )
                .agg(Pronostico=("Pronostico_Recomendado", "sum"))
            )
            prueba_real = (
                demanda.loc[demanda["Fecha"].isin(fechas_prueba)]
                .groupby(
                    ["Fecha", "SKU", "Producto", "Categoria"],
                    as_index=False,
                )
                .agg(Venta_Real=("Demanda", "sum"))
            )
            detalle_prueba = prueba_real.merge(
                prueba_predicha,
                on=["Fecha", "SKU", "Producto", "Categoria"],
                how="left",
                validate="one_to_one",
            )
            detalle_prueba["Error"] = (
                detalle_prueba["Pronostico"]
                - detalle_prueba["Venta_Real"]
            )
            detalle_prueba["Error_Absoluto"] = detalle_prueba[
                "Error"
            ].abs()
            total_real = detalle_prueba["Venta_Real"].sum()
            diagnostico["backtest_disponible"] = True
            diagnostico["backtest_wape"] = (
                detalle_prueba["Error_Absoluto"].sum()
                / total_real * 100
            )
            diagnostico["backtest_sesgo"] = (
                detalle_prueba["Error"].sum() / total_real * 100
            )
            diagnostico["backtest_inicio"] = inicio_prueba
            diagnostico["backtest_fin"] = pd.Timestamp(
                fechas_prueba[-1]
            )
            diagnostico["backtest_detalle"] = detalle_prueba
        robustez = None
        detalle_modelos = None
        es_caso_validado = False

    if "Metodo_Reparto" not in futuro.columns:
        futuro["Metodo_Reparto"] = (
            "Participación histórica del mismo mes"
        )
    futuro = enriquecer_pronostico_financiero(futuro, catalogo)
    for tabla in [demanda, futuro]:
        tabla["Fecha"] = pd.to_datetime(tabla["Fecha"])
    return (
        ventas_originales, demanda, futuro, diagnostico, robustez,
        detalle_modelos,
        es_caso_validado,
    )
