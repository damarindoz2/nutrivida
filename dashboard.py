"""Dashboard narrativo del caso de demanda NutriVida.

Ejecución desde la carpeta del proyecto:
    ../.venv/bin/streamlit run dashboard.py

La aplicación cuenta primero qué se encontró, qué se decidió y por qué. Después
permite comparar escenarios y hacer ajustes manuales visibles.
"""

from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from flujo_analisis import ejecutar_flujo_analisis
from limpieza_datos import validar_plantilla
from modelo_demanda import promedio_ponderado


CARPETA = Path(__file__).parent
ARCHIVO_ORIGINAL = CARPETA / "Datos_NutriVida.xlsx"
ARCHIVO_PRONOSTICO = (
    CARPETA / "resultados" / "Pronostico_NutriVida_2026_FINAL.xlsx"
)

@st.cache_data(show_spinner=False)
def cargar_datos(origen_bytes=None):
    """Conserva en caché el flujo de análisis para que la interfaz sea ágil."""
    return ejecutar_flujo_analisis(
        origen_bytes,
        ARCHIVO_ORIGINAL,
        ARCHIVO_PRONOSTICO,
    )


@st.cache_data(show_spinner=False)
def cargar_comparacion_empresa(origen_bytes=None):
    """Carga la comparación mensual entregada por la empresa, si existe."""
    origen = (
        BytesIO(origen_bytes)
        if origen_bytes is not None
        else ARCHIVO_ORIGINAL
    )
    try:
        tabla = pd.read_excel(origen, sheet_name="Pronostico vs Real")
    except (ValueError, KeyError):
        return None
    columnas = {"Fecha", "Pronostico_Empresa", "Venta_Real"}
    if not columnas.issubset(tabla.columns):
        return None
    tabla = tabla.copy()
    tabla["Fecha"] = pd.to_datetime(tabla["Fecha"], errors="coerce")
    return (
        tabla.dropna(subset=["Fecha"])
        .groupby("Fecha", as_index=False)[
            ["Pronostico_Empresa", "Venta_Real"]
        ]
        .sum()
    )


def descargar_excel(tabla):
    """Convierte una tabla en Excel descargable."""
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        tabla.to_excel(escritor, sheet_name="Resultado", index=False)
    return salida.getvalue()

MESES_CORTOS_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def eje_meses_espanol(figura, fechas):
    """Muestra meses en español sin convertir el eje temporal en texto."""
    fechas_unicas = sorted(pd.to_datetime(pd.Series(fechas).dropna().unique()))
    etiquetas = [
        f"{MESES_CORTOS_ES[fecha.month]}<br>{fecha.year}"
        for fecha in fechas_unicas
    ]
    figura.update_xaxes(
        tickmode="array",
        tickvals=fechas_unicas,
        ticktext=etiquetas,
        title_text="Mes",
    )
    return figura


LIMPIEZA_CASO = pd.DataFrame(
    [
        ["Variante de Ecommerce", "E-commerce", "Cambiar a Ecommerce", "Es otra escritura del canal Ecommerce; no se mezcla con Supermercado"],
        ["Variantes de Supermercado", "Super y SUPERMERCADO", "Cambiar a Supermercado", "Son otras escrituras de Supermercado; no se mezclan con Ecommerce"],
        ["Duplicados exactos", "28 filas involucradas; 14 copias", "Eliminar sólo la copia", "Quedaron las 8,100 claves esperadas"],
        ["Precios unitarios vacíos", "19 filas", "Completar con catálogo", "Todas las referencias coincidían"],
        ["Unidades negativas", "9 filas; impacto 7,378", "Usarlas como cero para modelar", "Así reconciliaban con Venta_Real"],
        ["Unidades vacías", "28 filas", "Conservar original y estimar aparte", "Vacío y cero no son iguales"],
        ["Ceros continuos de Azúcar", "54 ceros durante seis meses", "Tratar SKU-1021 como pausado", "También desaparecen pronóstico e inventario"],
        ["Valor atípico 13,380", "SKU-1001, marzo 2025", "Usar 1,533.25 sólo para modelar", "Rompía su historia y los consolidados"],
        ["Promoción sólo indica 0 o 1", "Sin descuento, duración ni tipo", "Medir historia y declarar límite", "No inventar intensidad futura"],
    ],
    columns=["Situación", "Se encontró", "Decisión", "Por qué"],
)

MODELOS_PRELIMINARES = pd.DataFrame(
    [
        ["Último dato", 22.31, -9.46, "Muy sensible al último mes"],
        ["Promedio últimos 3", 17.98, -8.18, "Suaviza, pero ignora temporada"],
        ["Empresa", 19.68, 4.23, "Referencia entregada"],
        ["Mismo mes anterior", 11.46, -5.47, "Captura temporada"],
        ["Promedio estacional", 12.23, -7.37, "Promedia años disponibles"],
        ["Ponderado inicial", 11.24, -5.37, "Combina nivel y estacionalidad"],
    ],
    columns=["Modelo", "Error_total_pct", "Balance_neto_pct", "Conclusión"],
)

MODELOS_FINALES = pd.DataFrame(
    [
        ["Pronóstico entregado por la empresa", 19.22, 7.69, 5.76, 13.46, "Comparador; su fórmula no fue proporcionada"],
        ["Mismo mes anterior", 11.59, -5.57, 8.58, 3.01, "Referencia simple"],
        ["Promedio reciente + estacionalidad", 11.71, -1.45, 6.58, 5.13, "Precursor del modelo final"],
        ["Modelo final + promociones conocidas", 8.10, -2.44, 5.27, 2.83, "Ideal; requiere un calendario de promociones"],
        ["Modelo final + promociones recurrentes", 10.56, -5.35, 7.96, 2.61, "Estimación central realista 2026"],
        ["Modelo final recurrente + protección 8%", 10.61, 2.22, 4.19, 6.42, "Escenario para reducir faltantes"],
    ],
    columns=["Modelo", "Error_total_pct", "Balance_neto_pct", "Faltante_pct", "Exceso_pct", "Uso"],
)

RECORRIDO_MODELOS = pd.DataFrame(
    [
        [
            "Pronóstico entregado por la empresa",
            "Se tomó directamente Pronostico_Empresa de la hoja Pronostico vs Real; su fórmula no fue proporcionada ni reconstruida.",
            "Error total de 19.22 por cada 100 unidades reales; en conjunto proyectó 7.69 unidades de más por cada 100.",
            "Se conserva como comparador: es el proceso actual contra el que debe medirse la propuesta.",
        ],
        [
            "Último dato",
            "Se repitió para cada SKU el último mes conocido.",
            "En la primera prueba: error total de 22.31 por cada 100 unidades reales; en conjunto quedó 9.46 unidades corto.",
            "Descartado: depende demasiado de un solo mes y no reconoce temporada.",
        ],
        [
            "Promedio de los últimos tres meses",
            "Se promediaron los tres meses anteriores para suavizar cambios bruscos.",
            "En la primera prueba: error total de 17.98 por cada 100 unidades reales; en conjunto quedó 8.18 unidades corto.",
            "Descartado como modelo principal: mejora al último dato, pero sigue ignorando que cada mes del año es diferente.",
        ],
        [
            "Mismo mes del año anterior",
            "Para pronosticar, por ejemplo, marzo de 2025 se repitió marzo de 2024 del mismo SKU.",
            "Error total de 11.59 por cada 100 unidades reales; en conjunto quedó 5.57 unidades corto.",
            "Se conserva como referencia sencilla: capta temporada, pero no adapta bien los cambios recientes ni las promociones.",
        ],
        [
            "Meses recientes ponderados + estacionalidad",
            "Se retiró el efecto del mes, se ponderaron los tres meses recientes y después se recuperó la temporada futura.",
            "Error total de 11.71 por cada 100 unidades reales; en conjunto quedó 1.45 unidades corto.",
            "Fue precursor: equilibró mejor los faltantes y excesos, pero todavía mezclaba el efecto promocional con la demanda normal.",
        ],
        [
            "Modelo final + promociones conocidas",
            "Se separaron las promociones, se promediaron los dos meses comparables más recientes y se aplicó el calendario promocional que realmente ocurrió.",
            "Error total de 8.10 por cada 100 unidades reales; en conjunto quedó 2.44 unidades corto.",
            "Es el mejor resultado ideal, pero no puede prometerse para 2026 sin recibir un calendario de promociones futuras.",
        ],
        [
            "Modelo final + promociones recurrentes",
            "Se utilizó el promedio de los dos meses comparables más recientes y la estacionalidad; sólo se infirió una promoción si el mismo SKU y mes la tuvo en al menos dos años conocidos.",
            "Error total de 10.56 por cada 100 unidades reales: 7.96 fueron faltantes pronosticados y 2.61 fueron excesos; el balance quedó 5.35 unidades corto.",
            "Elegido como pronóstico central 2026: es la mejor opción realista con la información disponible.",
        ],
        [
            "Modelo final recurrente + protección 8%",
            "Se multiplicó el pronóstico recomendado por 1.08 para probar una política que prioriza evitar faltantes.",
            "Error total de 10.61 por cada 100 unidades reales: 4.19 fueron faltantes pronosticados y 6.42 fueron excesos; el balance quedó 2.22 unidades por encima.",
            "Se muestra aparte: reduce faltantes, pero aumenta excedente; es una decisión de riesgo y no otro pronóstico central.",
        ],
    ],
    columns=["Alternativa", "Qué se hizo", "Resultado", "Decisión"],
)

HALLAZGOS_NEGOCIO = pd.DataFrame(
    [
        ["Inventario", "Stock final y venta perdida reproducen exactamente sus fórmulas"],
        ["Cobertura", "Stock final / venta real × 30 reproduce todos los registros"],
        ["Nivel de servicio", "97.49% por unidades en 2025; no reproduce el 96% declarado"],
        ["Rotación", "Aproximación estándar 11.03; no reproduce las 5.1 veces declaradas"],
        ["Margen", "Margen bruto ponderado aproximado de 30.86%"],
        ["Resumen gerencial", "El total supera la suma regional en USD 946,107"],
        ["Stock y faltantes", "Si queda stock no reportan venta perdida; si llega a cero, sí"],
        ["Catálogo", "Cada SKU corresponde a un solo producto, categoría y precio"],
    ],
    columns=["Tema", "Descubrimiento"],
)


st.set_page_config(
    page_title="NutriVida | Caso de demanda", page_icon="📈", layout="wide"
)
st.title("Caso NutriVida · análisis y pronóstico de demanda")
st.caption(
    "De los datos originales a una decisión explicable: limpieza, pruebas, "
    "supuestos, pronóstico y escenarios de riesgo."
)

with st.sidebar:
    st.header("Archivo de trabajo")
    archivo_subido = st.file_uploader(
        "Cargar un Excel completo para recalcular todo", type=["xlsx"]
    )
    with st.expander("Columnas mínimas del Excel nuevo"):
        st.markdown(
            "**Hoja `Ventas Historicas`**\n\n"
            "`Fecha`, `SKU`, `Producto`, `Categoria`, `Canal`, `Region`, "
            "`Unidades`, `Precio_Unitario_USD`, `Promocion`.\n\n"
            "**Hoja `Precios y Costos`**\n\n"
            "`SKU`, `Precio_Venta_USD`, `Margen_Bruto_pct`, "
            "`Costo_Almacenaje_Mes_USD_Unid`, `Vida_Util_Meses`.\n\n"
            "Puede contener columnas y hojas adicionales. `Pronostico vs Real` "
            "e `Inventario y Quiebres` son opcionales para el nuevo cálculo; "
            "si están presentes, se usan como controles de reconciliación."
        )
    bytes_subidos = archivo_subido.getvalue() if archivo_subido else None
    recalcular_excel_local = st.toggle(
        "Releer Datos_NutriVida.xlsx desde disco",
        value=False,
        disabled=archivo_subido is not None,
        help=(
            "Úsalo si editas directamente el Excel de la carpeta. Repite la "
            "limpieza, el backtest y el pronóstico en lugar de abrir el resultado "
            "precalculado."
        ),
    )
    bytes_fuente_modelo = bytes_subidos
    if archivo_subido is None and recalcular_excel_local:
        bytes_fuente_modelo = ARCHIVO_ORIGINAL.read_bytes()
        st.button("Volver a leer el Excel local")
    if archivo_subido:
        errores, _ = validar_plantilla(bytes_subidos)
        if errores:
            for error in errores:
                st.error(error)
            st.stop()
        st.success("La plantilla contiene las hojas y columnas mínimas")
    elif recalcular_excel_local:
        errores, _ = validar_plantilla(bytes_fuente_modelo)
        if errores:
            for error in errores:
                st.error(error)
            st.stop()
        st.success("Modo dinámico: se recalcula desde Datos_NutriVida.xlsx")
    else:
        st.success("Caso validado: Datos_NutriVida.xlsx")
    st.markdown("**Orden sugerido para recorrerlo**")
    st.markdown(
        "1. Cómo venía la empresa\n"
        "2. Pronóstico y filtros\n"
        "3. Comparación de alternativas\n"
        "4. Metodología y detalle"
    )

try:
    (
        ventas,
        demanda,
        futuro,
        diagnostico,
        robustez,
        detalle_modelos,
        es_caso_validado,
    ) = (
        cargar_datos(bytes_fuente_modelo)
    )
except Exception as error:
    st.error(f"No fue posible procesar el archivo: {error}")
    st.stop()

comparacion_empresa = cargar_comparacion_empresa(bytes_fuente_modelo)

if not es_caso_validado:
    if diagnostico.get("backtest_disponible"):
        st.warning(
            "La fuente dinámica pasó la validación, recibió el mismo método y "
            "se evaluó ocultando sus últimos seis meses. Sus métricas aparecen "
            "por separado; 10.56% y 19.22% pertenecen al caso original."
        )
    else:
        st.warning(
            "La fuente dinámica pasó la validación y recibió el mismo método, "
            "pero no tiene historia suficiente para reservar seis meses de "
            "prueba. No debe heredar el porcentaje de error del caso original."
        )
    diferencias_pronostico = diagnostico.get(
        "reconciliacion_pronostico_real_fuente_diferencias", 0
    )
    diferencias_inventario = diagnostico.get(
        "reconciliacion_inventario_fuente_diferencias", 0
    )
    if diferencias_pronostico or diferencias_inventario:
        st.warning(
            "El Excel capturado ya no coincide por completo con "
            f"las hojas consolidadas: {diferencias_pronostico} claves frente a "
            f"Pronostico vs Real y {diferencias_inventario} frente a Inventario "
            "y Quiebres. El modelo usa Ventas Historicas; conviene actualizar también "
            "los consolidados o explicar la diferencia."
        )
    errores_formula_inventario = sum(
        diagnostico.get(clave, 0)
        for clave in [
            "inventario_formula_stock_diferencias",
            "inventario_formula_perdida_diferencias",
            "inventario_formula_cobertura_diferencias",
        ]
    )
    if errores_formula_inventario:
        st.warning(
            "Los cambios del Excel dejaron fórmulas de inventario sin "
            f"reconciliar ({errores_formula_inventario} comprobaciones con "
            "diferencia entre stock final, venta perdida o días de cobertura)."
        )

inicio_pronostico = pd.Timestamp(futuro["Fecha"].min())
fin_pronostico = pd.Timestamp(futuro["Fecha"].max())
anio_pronostico = inicio_pronostico.year
MESES_LARGOS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}
if inicio_pronostico.year == fin_pronostico.year:
    periodo_pronostico = (
        f"{MESES_LARGOS_ES[inicio_pronostico.month]}–"
        f"{MESES_LARGOS_ES[fin_pronostico.month]} de "
        f"{inicio_pronostico.year}"
    )
else:
    periodo_pronostico = (
        f"{MESES_LARGOS_ES[inicio_pronostico.month]} de "
        f"{inicio_pronostico.year}–"
        f"{MESES_LARGOS_ES[fin_pronostico.month]} de "
        f"{fin_pronostico.year}"
    )

with st.expander("Glosario básico antes de empezar"):
    gl1, gl2 = st.columns(2)
    with gl1:
        st.markdown(
            "**SKU:** identificador único de un producto. Aquí cada SKU tiene "
            "un solo producto y categoría.\n\n"
            "**Demanda:** unidades que los clientes querían comprar. Puede ser "
            "mayor que la venta atendida cuando faltó inventario.\n\n"
            "**Pronóstico:** estimación de una demanda futura que todavía no "
            "ha ocurrido.\n\n"
            "**Modelo:** conjunto de reglas o cálculos que convierte el historial "
            "en un pronóstico."
        )
    with gl2:
        st.markdown(
            "**Backtest o validación histórica:** ocultar un periodo ya conocido, "
            "pronosticarlo usando sólo datos anteriores y comparar contra lo que "
            "realmente ocurrió.\n\n"
            "**Escenario:** una alternativa para tomar decisiones; no implica que "
            "todas las alternativas sean igualmente probables.\n\n"
            "**KPI:** indicador resumido para evaluar un resultado.\n\n"
            "**Balance neto del error:** indica si, al sumar todo, el pronóstico "
            "tendió a quedarse corto o a proyectar de más."
        )

tab_resumen, tab_pronostico, tab_modelos, tab_metodologia = st.tabs(
    [
        "1 · Cómo venía la empresa",
        f"2 · Pronóstico {periodo_pronostico}",
        "3 · Comparación de alternativas",
        "4 · Metodología y detalle",
    ]
)
tab_limpieza = tab_metodologia
tab_robustez = tab_metodologia
tab_detalle = tab_metodologia
tab_notas = tab_metodologia

with tab_resumen:
    st.header("Cómo venía la empresa con los datos recibidos")
    ultimo_anio = int(demanda["Fecha"].dt.year.max())
    demanda_ultimo_anio = demanda.loc[
        demanda["Fecha"].dt.year.eq(ultimo_anio), "Demanda"
    ].sum()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Historia disponible", f"{demanda['Fecha'].nunique()} meses")
    k2.metric(
        f"Unidades analizadas en {ultimo_anio}",
        f"{demanda_ultimo_anio:,.0f}",
    )
    if es_caso_validado:
        k3.metric("Error total · empresa", "19.22 por cada 100")
        k4.metric("Error total · recomendado", "10.56 por cada 100", "-8.66")
    elif diagnostico.get("backtest_disponible"):
        k3.metric(
            "Error total de la prueba",
            f"{diagnostico['backtest_wape']:.2f} por cada 100",
        )
        k4.metric(
            "Balance neto de la prueba",
            f"{diagnostico['backtest_sesgo']:+.2f}%",
        )
    else:
        k3.metric("Backtest de la fuente dinámica", "Pendiente")
        k4.metric("Método aplicado", "Recalculado")
    if es_caso_validado or diagnostico.get("backtest_disponible"):
        st.caption(
            "El error total indica cuántas unidades de diferencia absoluta acumuló "
            "el pronóstico por cada 100 unidades reales. Cuenta tanto lo que faltó "
            "como lo que sobró; un valor menor es mejor."
        )
    st.subheader("Pronóstico entregado por la empresa frente a la venta real")
    if comparacion_empresa is not None:
        historia_empresa = comparacion_empresa.rename(
            columns={
                "Pronostico_Empresa": "Pronóstico entregado por la empresa",
                "Venta_Real": "Venta real reportada",
            }
        ).melt("Fecha", var_name="Serie", value_name="Unidades")
        figura_historia_empresa = px.line(
            historia_empresa,
            x="Fecha",
            y="Unidades",
            color="Serie",
            markers=True,
        )
        eje_meses_espanol(figura_historia_empresa, historia_empresa["Fecha"])
        st.plotly_chart(
            figura_historia_empresa,
            width="stretch",
            key="historia_empresa_resumen",
        )
        st.caption(
            "Ambas líneas provienen de la hoja Pronostico vs Real y están "
            "sumadas por mes para los 25 productos. La hoja comienza en febrero "
            "de 2023 y termina en diciembre de 2025."
        )
    else:
        st.info(
            "El archivo cargado no incluye la hoja Pronostico vs Real; por eso "
            "no es posible dibujar esta comparación."
        )
    st.info(
        "La comparación histórica indica que el pronóstico recibido acumuló "
        "19.22 unidades de diferencia por cada 100 unidades reales. La "
        "alternativa propuesta redujo esa diferencia a 10.56 en las pruebas "
        "con periodos cuyos resultados ya eran conocidos."
        if es_caso_validado
        else "El archivo cargado se evalúa ocultando sus últimos meses conocidos; "
        "la comparación aparece en la sección de alternativas."
    )
    with st.expander("Decisiones principales del análisis"):
        c1, c2, c3, c4 = st.columns(4)
        with c1.container(border=True):
            st.markdown("**Conservar el original**")
            st.write("Los ajustes viven en columnas separadas y con banderas.")
        with c2.container(border=True):
            st.markdown("**Pronosticar por producto**")
            st.write("Cada SKU se calcula individualmente.")
        with c3.container(border=True):
            st.markdown("**Reconocer la temporada**")
            st.write("Un mes alto no se compara como si fuera un mes normal.")
        with c4.container(border=True):
            st.markdown("**Separar protección**")
            st.write("El 8% es una decisión de riesgo, no demanda esperada.")

with tab_limpieza:
    st.header("Qué se encontró en los datos y qué se hizo")
    st.write("La regla principal fue no confundir corregir con inventar. El dato original permanece intacto y la versión para modelar deja trazabilidad.")
    f1, f2, f3, f4, f5, f6 = st.columns(6)
    f1.metric("Filas recibidas", f"{diagnostico['filas_originales']:,}")
    f2.metric("Filas limpias", f"{diagnostico['filas_limpias']:,}")
    f3.metric("Unidades vacías", diagnostico["unidades_vacias"])
    f4.metric("Unidades negativas", diagnostico["unidades_negativas"])
    f5.metric("Precios vacíos", diagnostico["precios_vacios"])
    f6.metric(
        "Atípicos ajustados",
        diagnostico.get("atipicos_altos_ajustados", 0),
    )
    st.dataframe(LIMPIEZA_CASO, width="stretch", hide_index=True)
    if not es_caso_validado:
        with st.expander("Reconciliación del Excel modificado"):
            st.write(
                "El pronóstico se recalcula desde `Ventas Historicas`. Si se "
                "modifica una unidad ahí pero no en las hojas consolidadas, "
                "se muestra la diferencia en vez de ocultarla."
            )
            for titulo, clave in [
                ("Pronostico vs Real", "pronostico_real"),
                ("Inventario y Quiebres", "inventario"),
            ]:
                if diagnostico.get(f"reconciliacion_{clave}_disponible"):
                    cantidad_fuente = diagnostico.get(
                        f"reconciliacion_{clave}_fuente_diferencias", 0
                    )
                    cantidad_modelo = diagnostico.get(
                        f"reconciliacion_{clave}_diferencias", 0
                    )
                    st.markdown(
                        f"**{titulo}: {cantidad_fuente} diferencias desde el "
                        f"Excel capturado; {cantidad_modelo} después de limpiar**"
                    )
                    detalle_fuente = diagnostico.get(
                        f"reconciliacion_{clave}_fuente_detalle"
                    )
                    if cantidad_fuente and detalle_fuente is not None:
                        st.caption(
                            "Estas diferencias indican que una hoja fue editada "
                            "sin actualizar la otra."
                        )
                        st.dataframe(
                            detalle_fuente,
                            width="stretch",
                            hide_index=True,
                        )
                    if cantidad_modelo:
                        st.caption(
                            "Las diferencias posteriores a limpiar pueden ser "
                            "deliberadas; en el caso original provienen de retirar "
                            "duplicados exactos."
                        )
            st.markdown(
                "**Fórmulas de inventario:** "
                f"{diagnostico.get('inventario_formula_stock_diferencias', 0)} "
                "diferencias en stock final, "
                f"{diagnostico.get('inventario_formula_perdida_diferencias', 0)} "
                "en venta perdida y "
                f"{diagnostico.get('inventario_formula_cobertura_diferencias', 0)} "
                "en días de cobertura."
            )
    st.info(
        "Ecommerce, Mayorista y Supermercado permanecen como tres canales "
        "diferentes. Sólo se homologaron variantes de escritura dentro de cada "
        "canal: E-commerce → Ecommerce; Super y SUPERMERCADO → Supermercado. "
        "El pronóstico central suma después los canales para compararse al "
        "nivel SKU-mes de la empresa y del inventario central; sumarlos no "
        "significa considerarlos equivalentes."
    )
    with st.expander("Cómo se estimaron las 28 unidades vacías"):
        st.write("Se comparó cada SKU-canal-región con el mes anterior, el siguiente y el mismo mes de otros años. En promoción se estimó una base y luego se aplicó el factor histórico del SKU. El original siguió vacío; el resultado vive en Unidades_Modelo.")
        st.markdown(
            "**Referencia temporal:** "
            "`promedio(mes anterior, mes siguiente)`. Captura lo que ocurría "
            "alrededor del vacío. Si sólo existe uno de los dos, usa únicamente "
            "el disponible.\n\n"
            "**Referencia estacional:** `promedio del mismo SKU, canal, región "
            "y mes calendario en otros años`. Captura que enero puede comportarse "
            "distinto de julio.\n\n"
            "**Propuesta combinada:** `promedio(referencia temporal, referencia "
            "estacional)`. Si una no existe, se usa la disponible.\n\n"
            "**Vacío promocional:** primero se estima cuánto habría vendido sin "
            "campaña y después se multiplica por el efecto histórico de promoción "
            "del SKU."
        )
        st.write("Métodos finales: 23 promedios temporal-estacionales, 3 bases sin promoción por factor del SKU y 2 respaldos estacionales.")
    with st.expander("Por qué los negativos se convirtieron en cero"):
        st.write("Se sumaron las nueve combinaciones canal-región y se compararon con Venta_Real. El consolidado sólo coincidió al tratar las nueve cifras negativas como cero.")
    with st.expander("Por qué Azúcar se considera pausada"):
        st.write("Desde julio de 2025 aparecen nueve ceros mensuales. Desde agosto también desaparecen pronóstico e inventario: evidencia de pausa, no de estacionalidad cero.")
    st.subheader("Otros descubrimientos al reconciliar las hojas")
    st.dataframe(HALLAZGOS_NEGOCIO, width="stretch", hide_index=True)
    with st.expander("Fórmulas de inventario y negocio, explicadas"):
        st.markdown(
            "**Stock final**\n\n"
            "`máximo(stock inicial - venta real, 0)`\n\n"
            "Son las unidades que quedan. Nunca se permite un inventario negativo.\n\n"
            "**Venta perdida**\n\n"
            "`máximo(venta real - stock inicial, 0)`\n\n"
            "Es la parte de la demanda que no pudo atenderse porque el inventario "
            "no alcanzó. En este archivo ambas fórmulas coinciden en todas las filas.\n\n"
            "**Días de cobertura**\n\n"
            "`stock final / venta real del mes × 30`\n\n"
            "Aproxima cuántos días duraría el inventario final si continuara el "
            "ritmo de venta del mismo mes. Si la venta es cero, no puede dividirse "
            "y el resultado queda vacío.\n\n"
            "**Nivel de servicio por unidades**\n\n"
            "`venta atendida / demanda × 100`\n\n"
            "De cada 100 unidades solicitadas, indica cuántas pudieron entregarse. "
            "Con esta definición se obtuvo 97.49% en 2025; no reproduce el 96% "
            "declarado.\n\n"
            "**Nivel de servicio por ciclos**\n\n"
            "`SKU-meses sin venta perdida / total de SKU-meses × 100`\n\n"
            "Pregunta en cuántos periodos no hubo ningún faltante, aunque haya sido "
            "de una sola unidad. Por eso puede diferir mucho del servicio por unidades.\n\n"
            "**Margen bruto porcentual**\n\n"
            "`(ingreso - costo del producto) / ingreso × 100`\n\n"
            "Mide cuánto queda de cada dólar vendido antes de otros gastos. El archivo "
            "da el porcentaje, así que el costo unitario se aproximó como "
            "`precio × (1 - margen)`.\n\n"
            "**Rotación de inventario**\n\n"
            "`costo de ventas anual / valor promedio del inventario`\n\n"
            "Indica cuántas veces, aproximadamente, se renueva el inventario en un "
            "año. Se obtuvo 11.03, pero es una aproximación porque faltan costo "
            "contable real y movimientos de compra; por eso no se afirma que 5.1 "
            "sea incorrecto, sólo que no se reproduce con lo entregado."
        )

with tab_modelos:
    st.header("Qué modelos se probaron y por qué")
    if es_caso_validado and detalle_modelos is not None:
        st.subheader("Lo que realmente pasó frente a cada alternativa")
        validacion_mensual = detalle_modelos["Validación 2025"].copy()
        columnas_validacion = {
            "Venta_Real": "Venta real",
            "Pronostico_Empresa": "Pronóstico de la empresa",
            "Pronostico_Mismo_Mes_Anterior": "Mismo mes del año anterior",
            "Pronostico_Ponderado_Estacional": "Promedio reciente + estacionalidad",
            "Pronostico_Recomendado": "Recomendado",
            "Pronostico_Protegido": "Protegido 8%",
        }
        validacion_mensual_ancha = (
            validacion_mensual.groupby("Fecha", as_index=False)[
                list(columnas_validacion)
            ]
            .sum()
            .rename(columns=columnas_validacion)
        )
        alternativas_visibles = st.multiselect(
            "Líneas que quieres comparar",
            list(columnas_validacion.values()),
            default=[
                "Venta real",
                "Pronóstico de la empresa",
                "Recomendado",
            ],
            key="alternativas_validacion_general",
        )
        if alternativas_visibles:
            validacion_mensual = validacion_mensual_ancha.melt(
                "Fecha",
                value_vars=alternativas_visibles,
                var_name="Alternativa",
                value_name="Unidades",
            )
            figura_validacion_mensual = px.line(
                validacion_mensual,
                x="Fecha",
                y="Unidades",
                color="Alternativa",
                markers=True,
            )
            eje_meses_espanol(
                figura_validacion_mensual,
                validacion_mensual["Fecha"],
            )
            st.plotly_chart(
                figura_validacion_mensual,
                width="stretch",
                key="validacion_mensual_principal",
            )
        else:
            st.warning("Selecciona por lo menos una línea para mostrar la gráfica.")
        st.caption(
            "Ésta es una prueba histórica: para cada periodo se ocultaron esos "
            "meses, se pronosticaron sin mirar el resultado y después se "
            "compararon con la venta real. El selector permite concentrarse "
            "sólo en las alternativas que quieras revisar."
        )
    if not es_caso_validado:
        if diagnostico.get("backtest_disponible"):
            inicio_bt = diagnostico["backtest_inicio"].strftime("%Y-%m")
            fin_bt = diagnostico["backtest_fin"].strftime("%Y-%m")
            st.success(
                f"Validación recalculada para el archivo cargado ({inicio_bt} a "
                f"{fin_bt}): el error total fue "
                f"{diagnostico['backtest_wape']:.2f} por cada 100 unidades reales "
                f"y el balance neto fue {diagnostico['backtest_sesgo']:+.2f}%."
            )
            detalle_nuevo = diagnostico["backtest_detalle"].copy()
            mensual_nuevo = (
                detalle_nuevo.groupby("Fecha", as_index=False)
                .agg(
                    Venta_Real=("Venta_Real", "sum"),
                    Pronostico=("Pronostico", "sum"),
                )
                .melt(
                    "Fecha", var_name="Serie", value_name="Unidades"
                )
            )
            figura_nuevo = px.line(
                mensual_nuevo,
                x="Fecha",
                y="Unidades",
                color="Serie",
                markers=True,
                title="Pronóstico contra lo que realmente pasó",
            )
            eje_meses_espanol(figura_nuevo, mensual_nuevo["Fecha"])
            st.plotly_chart(
                figura_nuevo,
                width="stretch",
                key="backtest_archivo_nuevo",
            )
        else:
            st.warning(
                "El archivo cargado no tiene historia suficiente para separar "
                "una prueba de seis meses."
            )
        st.info(
            "Las comparaciones detalladas que siguen documentan el caso "
            "original y no deben confundirse con el resultado recién calculado."
        )
    g1, g2, g3, g4 = st.columns(4)
    for columna, titulo, texto in [
        (g1, "Error total", "Diferencia acumulada por cada 100 unidades reales. Menor es mejor."),
        (g2, "Balance neto", "Negativo: el pronóstico quedó corto. Positivo: proyectó de más."),
        (g3, "Faltante pronosticado", "Unidades reales que el pronóstico no alcanzó a cubrir."),
        (g4, "Exceso pronosticado", "Unidades proyectadas por encima de lo que ocurrió."),
    ]:
        with columna.container(border=True):
            st.markdown(f"**{titulo}**")
            st.write(texto)
    with st.expander("Cómo se mide el error del pronóstico"):
        st.markdown(
            "Primero se calcula el **error firmado** de cada fila:\n\n"
            "`error = pronóstico - venta real para modelar`\n\n"
            "Si da -20, faltaron 20 unidades en el pronóstico. Si da +20, el "
            "pronóstico tuvo 20 unidades de más."
        )
        st.latex(
            r"Error\ total\ (\%) = \frac{\sum |Pronostico - Real|}{\sum Real}\times 100"
        )
        st.markdown(
            "El **error total relativo** suma todos los errores sin permitir que "
            "los positivos y negativos se cancelen, y los compara contra toda la demanda real. "
            "Ejemplo: si se vendieron 1,000 unidades y los errores absolutos suman "
            "100, el resultado es 10%. Significa **10 unidades de diferencia por "
            "cada 100 unidades reales**. No significa automáticamente que el "
            "modelo tenga '90% de precisión'. Además, los SKU de mayor volumen "
            "pesan más en el resultado."
        )
        st.latex(
            r"Balance\ neto\ (\%) = \frac{\sum (Pronostico - Real)}{\sum Real}\times 100"
        )
        st.markdown(
            "El **balance neto** conserva el signo. Un resultado de -5% indica que, al sumar "
            "todo, el modelo quedó aproximadamente 5% por debajo; +5% indica que "
            "quedó por encima. Un balance cercano a cero no garantiza precisión: "
            "errores positivos y negativos pueden cancelarse."
        )
        st.latex(
            r"Faltante = \frac{\sum max(Real-Pronostico,0)}{\sum Real}\times 100"
        )
        st.latex(
            r"Exceso = \frac{\sum max(Pronostico-Real,0)}{\sum Real}\times 100"
        )
        st.markdown(
            "El **faltante pronosticado** cuenta sólo lo que faltó prever; se relaciona "
            "con el riesgo de quiebres. El **exceso pronosticado** cuenta sólo lo que sobró; "
            "se relaciona con inventario sobrante y posible merma. Con la misma "
            "base de comparación, `error total ≈ faltante + exceso` y "
            "`balance neto ≈ exceso - faltante`."
        )
    st.subheader("Qué es el pronóstico de la empresa")
    st.info(
        "No es un modelo construido en este proyecto. Es la columna "
        "Pronostico_Empresa que NutriVida entregó en la hoja Pronostico vs "
        "Real. Como no se recibió su fórmula, R² ni método, no se afirma cómo "
        "se calculó: sólo se utiliza como referencia del proceso actual. "
        "Se compara contra la misma venta real limpia y al mismo nivel "
        "SKU-mes que las alternativas evaluadas."
    )

    st.subheader("Recorrido de pruebas: qué se hizo, resultado y decisión")
    st.write(
        "El proceso no comenzó directamente con el modelo final. Primero se "
        "probaron referencias simples, después se añadió estacionalidad, se "
        "separaron las promociones y finalmente se evaluó una política de protección. "
        "Los resultados preliminares "
        "corresponden a la primera ventana; la comparación final utiliza las dos "
        "ventanas activas de 2025."
    )
    for numero, fila in RECORRIDO_MODELOS.iterrows():
        with st.expander(
            f"{numero + 1}. {fila['Alternativa']}",
            expanded=False,
        ):
            st.markdown(
                f"**Qué se hizo:** {fila['Qué se hizo']}\n\n"
                f"**Resultado:** {fila['Resultado']}\n\n"
                f"**Decisión:** {fila['Decisión']}"
            )
    st.subheader("Comparación final en las dos ventanas activas de 2025")
    st.plotly_chart(
        px.bar(
            MODELOS_FINALES,
            x="Modelo",
            y="Error_total_pct",
            color="Uso",
            text_auto=".2f",
            labels={
                "Error_total_pct": "Error por cada 100 unidades reales",
                "Uso": "Cómo se utiliza",
            },
        ),
        width="stretch",
        key="comparacion_modelos",
    )
    modelos_finales_mostrados = MODELOS_FINALES.rename(
        columns={
            "Error_total_pct": "Error por cada 100 unidades reales",
            "Balance_neto_pct": "Balance neto (%)",
            "Faltante_pct": "Faltante pronosticado (%)",
            "Exceso_pct": "Exceso pronosticado (%)",
        }
    )
    st.dataframe(
        modelos_finales_mostrados.style.format(
            {
                "Error por cada 100 unidades reales": "{:.2f}",
                "Balance neto (%)": "{:+.2f}%",
                "Faltante pronosticado (%)": "{:.2f}%",
                "Exceso pronosticado (%)": "{:.2f}%",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.success(
        "Se eligió el modelo de promedio reciente + estacionalidad + promociones "
        "recurrentes como estimación central: acumuló 10.56 unidades de error "
        "por cada 100 unidades reales, frente a 19.22 del pronóstico entregado "
        "por la empresa."
    )
    st.warning("El 8.10% conoce las promociones futuras. No debe prometerse sin recibir un calendario de promociones.")
    with st.expander(
        "Qué se probó y qué todavía no puede garantizar el modelo",
        expanded=False,
    ):
        probado, limite = st.columns(2)
        with probado:
            st.markdown(
                "**Sí quedó probado**\n\n"
                "- Dos backtests de seis meses: enero-junio y julio-diciembre de 2025.\n"
                "- Cada corte utiliza únicamente información que ya existía en esa fecha.\n"
                "- Los factores promocionales se aprendieron sólo con 2023-2024.\n"
                "- El promedio de los dos meses comparables más recientes se eligió en la primera ventana y se conservó en la segunda.\n"
                "- La regla de promoción recurrente también respeta cada fecha de corte.\n"
                "- Se midieron el error total, el balance neto, los faltantes y los excesos del pronóstico.\n"
                "- Se revisó robustez por los 25 SKU, categoría y mes.\n"
                "- El archivo final no tiene pronósticos vacíos, negativos ni claves repetidas.\n"
                "- Las tres regiones suman nuevamente al total de cada SKU."
            )
        with limite:
            st.markdown(
                "**No puede garantizarse todavía**\n\n"
                "- El resultado real de 2026: todavía no ha ocurrido.\n"
                "- Promociones futuras que no fueron proporcionadas.\n"
                "- Tipo, descuento y duración de cada promoción: sólo existe 0 o 1.\n"
                "- Lanzamientos, retiros o ajustes futuros no presentes en la historia.\n"
                "- Pronósticos confiables para SKU nuevos sin historial.\n"
                "- Que el 10.56% se repita exactamente en 2026.\n"
                "- Que todos los SKU tengan el mismo error: el indicador total es un resultado agregado.\n"
                "- Que Azúcar siga pausada; es una regla de negocio que debe confirmarse."
            )
    with st.expander("Primeras pruebas: cómo se descartaron modelos"):
        st.caption("Cifras de enero-junio de 2025; muestran el aprendizaje inicial, no sustituyen la comparación final.")
        modelos_preliminares_mostrados = MODELOS_PRELIMINARES.rename(
            columns={
                "Error_total_pct": "Error por cada 100 unidades reales",
                "Balance_neto_pct": "Balance neto (%)",
            }
        )
        st.dataframe(
            modelos_preliminares_mostrados.style.format(
                {
                    "Error por cada 100 unidades reales": "{:.2f}",
                    "Balance neto (%)": "{:+.2f}%",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    st.subheader("Cómo funciona el modelo final recomendado")
    st.markdown("1. Quita el efecto estimado de promociones históricas.\n2. Aprende meses altos y bajos por SKU.\n3. Promedia los dos meses comparables más recientes.\n4. Recupera la estacionalidad futura.\n5. Añade promoción si el mismo SKU-mes la tuvo en dos años.\n6. Reparte el total entre regiones.")
    with st.expander("Fórmulas del modelo elegido, paso a paso"):
        st.markdown(
            "**1. Factor promocional histórico**\n\n"
            "`venta durante promoción / venta base estimada sin promoción`\n\n"
            "Ejemplo: 180 unidades durante campaña frente a una base de 100 dan "
            "un factor 1.8. Se usa la mediana por SKU para que un caso extremo no "
            "domine.\n\n"
            "**2. Demanda sin promoción**\n\n"
            "`venta promocional / factor promocional`. Las filas sin promoción "
            "se conservan como están.\n\n"
            "**3. Índice estacional**\n\n"
            "`promedio del SKU en ese mes / promedio general del SKU`. Un índice "
            "1.20 significa que ese mes suele estar 20% por encima de un mes "
            "promedio; 0.80 significa 20% por debajo.\n\n"
            "**4. Demanda desestacionalizada**\n\n"
            "`demanda sin promoción / índice estacional`. Quita temporalmente el "
            "efecto del mes para poder comparar meses distintos.\n\n"
            "**5. Promedio reciente comparable**\n\n"
            "`(penúltimo mes comparable + último mes comparable) / 2`, usando "
            "las demandas sin promoción y sin el efecto estacional. También se "
            "probó incluir un tercer mes, pero la validación le asignó peso cero; "
            "por claridad, el cálculo final se explica como un promedio de dos.\n\n"
            "**6. Pronóstico base del mes futuro**\n\n"
            "`promedio reciente comparable × índice estacional del mes futuro`.\n\n"
            "**7. Promoción recurrente**\n\n"
            "Sólo se activa si el mismo SKU y mes calendario tuvo promoción en "
            "al menos dos años. `Multiplicador = 1 + proporción esperada × "
            "(factor promocional - 1)`. Después: `recomendado = base × multiplicador`.\n\n"
            "**8. Escenario protegido**\n\n"
            "`protegido = recomendado × 1.08`. Se probaron incrementos de 0%, "
            "2%, 4%, 6%, 8% y 10% en enero–junio de 2025. El 8% dejó el balance "
            "más cerca de cero (−0.45%); con 10% ya existía sobreestimación "
            "neta (+1.40%). Después se conservó el 8% sin cambios para validarlo "
            "en julio–diciembre. Es un colchón de riesgo, no otra estimación de "
            "la demanda esperada.\n\n"
            "**9. Reparto por canal y región**\n\n"
            "`pronóstico del detalle = pronóstico del SKU × participación histórica "
            "del canal-región para ese SKU y mes`. Si una combinación es nueva y "
            "aún no tiene historia para ese mes calendario, se usa como respaldo su "
            "participación general en la historia del SKU. Todas las combinaciones "
            "observadas suman 100% y regresan exactamente al total del SKU."
        )

    st.subheader("Cómo se ajustaron los modelos a los meses ocultados")
    st.write(
        "Aquí no se muestra 2026: se muestra la validación histórica de 2025. Para enero-junio, los "
        "modelos sólo conocían datos hasta diciembre de 2024; para julio-diciembre, "
        "sólo hasta junio de 2025. La línea real permite ver si siguieron la forma "
        "temporal, no únicamente su error total acumulado."
    )
    if detalle_modelos is None:
        st.info(
            "El archivo nuevo todavía no tiene predicciones históricas. Debe "
            "repetirse el backtest para dibujar esta comparación."
        )
    else:
        temporal = detalle_modelos["Validación 2025"].copy()
        temporal["Fecha"] = pd.to_datetime(temporal["Fecha"])
        tm1, tm2 = st.columns(2)
        categorias_temporales = sorted(temporal["Categoria"].unique())
        categoria_temporal = tm1.selectbox(
            "Categoría para la prueba temporal",
            categorias_temporales,
            index=(
                categorias_temporales.index("Lacteos")
                if "Lacteos" in categorias_temporales
                else 0
            ),
            key="modelo_temporal_categoria",
        )
        skus_temporales = sorted(
            temporal.loc[
                temporal["Categoria"].eq(categoria_temporal), "SKU"
            ].unique()
        )
        sku_temporal = tm2.selectbox(
            "SKU para la prueba temporal",
            skus_temporales,
            index=(
                skus_temporales.index("SKU-1001")
                if "SKU-1001" in skus_temporales
                else 0
            ),
            key="modelo_temporal_sku",
        )
        columnas_modelos_temporales = {
            "Pronóstico entregado por la empresa": "Pronostico_Empresa",
            "Mismo mes anterior": "Pronostico_Mismo_Mes_Anterior",
            "Promedio reciente + estacionalidad": "Pronostico_Ponderado_Estacional",
            "Modelo final recomendado": "Pronostico_Recomendado",
            "Modelo final + protección 8%": "Pronostico_Protegido",
        }
        modelos_visibles = st.multiselect(
            "Modelos que quieres comparar con la venta real",
            list(columnas_modelos_temporales),
            default=list(columnas_modelos_temporales),
            key="modelos_temporales_visibles",
        )
        bloque_temporal = temporal.loc[
            temporal["SKU"].eq(sku_temporal)
        ].sort_values("Fecha")
        columnas_visibles = [
            columnas_modelos_temporales[modelo]
            for modelo in modelos_visibles
        ]
        nombres_inversos = {
            columna: modelo
            for modelo, columna in columnas_modelos_temporales.items()
        }
        grafica_temporal = (
            bloque_temporal[
                ["Fecha", "Venta_Real"] + columnas_visibles
            ]
            .rename(
                columns={
                    "Venta_Real": "Venta real para modelar",
                    **nombres_inversos,
                }
            )
            .melt("Fecha", var_name="Serie", value_name="Unidades")
        )
        figura_temporal = px.line(
            grafica_temporal,
            x="Fecha",
            y="Unidades",
            color="Serie",
            markers=True,
            title=f"Backtest mensual · {sku_temporal}",
        )
        figura_temporal.add_vline(
            x=pd.Timestamp("2025-07-01").timestamp() * 1000,
            line_dash="dash",
            line_color="gray",
        )
        eje_meses_espanol(figura_temporal, grafica_temporal["Fecha"])
        st.plotly_chart(
            figura_temporal,
            width="stretch",
            key="modelos_backtest_temporal",
        )
        st.caption(
            "La línea punteada separa las dos pruebas de seis meses. Un modelo "
            "puede acercarse en total y aun así no seguir bien ciertos picos."
        )

        modelo_para_error = st.selectbox(
            "Modelo cuyo error quieres revisar mes por mes",
            list(columnas_modelos_temporales),
            index=list(columnas_modelos_temporales).index(
                "Modelo final recomendado"
            ),
            key="modelo_error_temporal",
        )
        sufijos_error = {
            "Pronóstico entregado por la empresa": "Empresa",
            "Mismo mes anterior": "Mismo_Mes_Anterior",
            "Promedio reciente + estacionalidad": "Ponderado_Estacional",
            "Modelo final recomendado": "Recomendado",
            "Modelo final + protección 8%": "Protegido",
        }
        sufijo = sufijos_error[modelo_para_error]
        columna_pronostico = columnas_modelos_temporales[modelo_para_error]
        errores_mes = bloque_temporal[
            [
                "Fecha",
                "Venta_Real",
                columna_pronostico,
                f"Error_{sufijo}",
                f"Error_pct_{sufijo}",
            ]
        ].rename(
            columns={
                "Venta_Real": "Venta_Real_Modelo",
                columna_pronostico: "Pronostico",
                f"Error_{sufijo}": "Error_Unidades",
                f"Error_pct_{sufijo}": "Error_pct",
            }
        )
        errores_mes["Tipo_Error"] = errores_mes["Error_Unidades"].apply(
            lambda error: (
                "Sobreestimó" if error > 0
                else "Subestimó" if error < 0
                else "Exacto"
            )
        )
        figura_errores = px.bar(
            errores_mes,
            x="Fecha",
            y="Error_Unidades",
            color="Tipo_Error",
            color_discrete_map={
                "Subestimó": "#d62728",
                "Sobreestimó": "#1f77b4",
                "Exacto": "#2ca02c",
            },
            title=f"Error mensual · {modelo_para_error}",
        )
        eje_meses_espanol(figura_errores, errores_mes["Fecha"])
        st.plotly_chart(
            figura_errores,
            width="stretch",
            key="modelo_error_por_mes",
        )
        st.dataframe(
            errores_mes.style.format(
                {
                    "Venta_Real_Modelo": "{:,.2f}",
                    "Pronostico": "{:,.2f}",
                    "Error_Unidades": "{:+,.2f}",
                    "Error_pct": "{:+.2f}%",
                }
            ),
            width="stretch",
            hide_index=True,
        )

with tab_pronostico:
    st.header(
        f"Pronóstico {periodo_pronostico} y escenarios"
    )
    st.write(
        "Primero se calcula la demanda esperada de cada producto y después se "
        "muestran tres maneras de utilizarla:"
    )
    significado1, significado2, significado3 = st.columns(3)
    with significado1.container(border=True):
        st.markdown("**Sin promociones futuras**")
        st.write(
            "Promedio reciente y temporada del producto, suponiendo que no "
            "habrá promociones en los meses proyectados."
        )
    with significado2.container(border=True):
        st.markdown("**Recomendado**")
        st.write(
            "Estimación central: añade una promoción sólo cuando se repitió "
            "para el mismo producto y mes en al menos dos años."
        )
    with significado3.container(border=True):
        st.markdown("**Protegido 8%**")
        st.write(
            "Recomendado más 8% para reducir faltantes; puede dejar mayor "
            "excedente y no representa una demanda más probable."
        )
    st.info(
        "**¿De dónde salió el 8%?** Se probaron aumentos de 0%, 2%, 4%, 6%, "
        "8% y 10% usando enero–junio de 2025. Con 8%, el balance entre quedar "
        "cortos y proyectar de más quedó en −0.45%, el más cercano a cero; con "
        "10% ya pasó a +1.40%. Después se mantuvo 8% sin modificarlo y se "
        "validó en julio–diciembre. Por eso es un escenario de protección "
        "probado, no una corrección escondida dentro de la demanda esperada."
    )
    control1, control2, control3, control4, control5 = st.columns(5)
    categorias = sorted(futuro["Categoria"].dropna().unique())
    categoria = control1.selectbox("Categoría", ["Todas"] + categorias, key="pronostico_categoria")
    base_sku = futuro if categoria == "Todas" else futuro.loc[futuro["Categoria"].eq(categoria)]
    productos_por_sku = (
        base_sku[["SKU", "Producto"]]
        .drop_duplicates("SKU")
        .set_index("SKU")["Producto"]
        .to_dict()
    )
    sku = control2.selectbox(
        "Producto",
        ["Todos"] + sorted(base_sku["SKU"].unique()),
        format_func=lambda valor: (
            "Todos los productos"
            if valor == "Todos"
            else f"{productos_por_sku.get(valor, '')} · {valor}"
        ),
        key="pronostico_sku",
    )
    canal = control3.selectbox("Canal", ["Todos"] + sorted(futuro["Canal"].dropna().unique()), key="pronostico_canal")
    region = control4.selectbox("Región", ["Todas"] + sorted(futuro["Region"].dropna().unique()), key="pronostico_region")
    escenario = control5.selectbox(
        "Escenario para mostrar",
        ["Recomendado", "Protegido 8%", "Sin promociones futuras"],
        key="pronostico_escenario",
    )
    explicaciones = {
        "Sin promociones futuras": (
            "Promedio reciente y temporada, sin añadir campañas futuras."
        ),
        "Recomendado": (
            "Demanda esperada más promociones recurrentes. Es la estimación central del "
            + (
                "caso validado."
                if es_caso_validado
                else "fuente dinámica, con su propio backtest."
            )
        ),
        "Protegido 8%": "Recomendado más 8%. Reduce faltantes, pero aumenta excedentes.",
    }
    st.info(f"**{escenario}:** {explicaciones[escenario]}")
    mascara = pd.Series(True, index=futuro.index)
    if categoria != "Todas": mascara &= futuro["Categoria"].eq(categoria)
    if sku != "Todos": mascara &= futuro["SKU"].eq(sku)
    if canal != "Todos": mascara &= futuro["Canal"].eq(canal)
    if region != "Todas": mascara &= futuro["Region"].eq(region)
    vista = futuro.loc[mascara].copy()
    nombres_columnas = {
        "Sin promociones futuras": "Pronostico_Base",
        "Recomendado": "Pronostico_Recomendado",
        "Protegido 8%": "Pronostico_Protegido",
    }
    columna_elegida = nombres_columnas[escenario]

    meses_es = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }
    fechas_disponibles = sorted(vista["Fecha"].unique())
    panel_ajustes = st.expander("Cambiar una cifra o aplicar una promoción")
    cambio1, cambio2, cambio3 = panel_ajustes.columns(3)
    mes_ejemplo = cambio1.selectbox(
        "Mes que quieres explicar o cambiar",
        fechas_disponibles,
        format_func=lambda fecha: (
            f"{meses_es[pd.Timestamp(fecha).month].capitalize()} "
            f"{pd.Timestamp(fecha).year}"
        ),
        key="pronostico_mes_ejemplo",
    )
    alcance_ajuste = cambio2.selectbox(
        "Alcance del cambio",
        ["Sólo el mes seleccionado", "Los seis meses filtrados"],
        key="alcance_ajuste",
    )
    es_sku_pausado = (
        sku != "Todos"
        and not vista.empty
        and vista["Estado_SKU"].eq("Pausado").all()
    )
    motivos_disponibles = [
        "Solicitud de ajuste",
        "Promoción confirmada",
        "Promoción descartada",
        "Corrección manual",
    ]
    if es_sku_pausado:
        motivos_disponibles.append("Reactivación de SKU pausado")
    motivo_ajuste = cambio3.selectbox(
        "Motivo del cambio",
        motivos_disponibles,
        key="motivo_ajuste",
    )

    ajuste1, ajuste2, ajuste3 = panel_ajustes.columns(3)
    usar_factor_historico = False
    tabla_reactivacion = None
    if motivo_ajuste == "Reactivación de SKU pausado":
        ajuste_pct = 0.0
        ajuste_unidades = 0.0
        excluir = False
        alcance_reactivacion = []
        if canal != "Todos":
            alcance_reactivacion.append(f"canal {canal}")
        if region != "Todas":
            alcance_reactivacion.append(f"región {region}")
        texto_alcance_reactivacion = (
            " y ".join(alcance_reactivacion)
            if alcance_reactivacion
            else "todos los canales y regiones"
        )
        panel_ajustes.info(
            "Escribe las unidades que se reciban para cada mes. "
            f"Cada cifra será el total mensual del SKU para {texto_alcance_reactivacion}. "
            "Estos valores informados sustituyen el cero causado por la pausa; "
            "no son una estimación estadística."
        )
        tabla_reactivacion = panel_ajustes.data_editor(
            pd.DataFrame(
                {
                    "Fecha": pd.to_datetime(fechas_disponibles),
                    "Demanda_Informada": 0.0,
                }
            ),
            column_config={
                "Fecha": st.column_config.DateColumn(
                    "Mes",
                    format="MMM YYYY",
                    disabled=True,
                ),
                "Demanda_Informada": st.column_config.NumberColumn(
                    "Demanda informada (unidades)",
                    min_value=0.0,
                    step=1.0,
                    format="%.0f",
                ),
            },
            disabled=["Fecha"],
            hide_index=True,
            width="stretch",
            key="tabla_reactivacion_sku",
        )
        panel_ajustes.caption(
            "Si recibes un Excel corregido, basta cargarlo: la tabla sólo sirve "
            "cuando se proporcionan datos manualmente."
        )
    elif motivo_ajuste == "Promoción confirmada":
        metodo_promocion = ajuste1.selectbox(
            "Efecto de la promoción",
            ["Usar factor histórico del SKU", "Escribir porcentaje manual"],
            key="metodo_promocion",
        )
        usar_factor_historico = metodo_promocion == "Usar factor histórico del SKU"
        ajuste_pct = (
            0.0
            if usar_factor_historico
            else ajuste2.number_input(
                "Aumento promocional (%)",
                -100.0,
                300.0,
                0.0,
                5.0,
                key="ajuste_pct_promocion",
            )
        )
        ajuste_unidades = ajuste3.number_input(
            "Unidades adicionales",
            -1_000_000.0,
            1_000_000.0,
            0.0,
            100.0,
            key="ajuste_unidades_promocion",
        )
        excluir = False
    elif motivo_ajuste == "Promoción descartada":
        ajuste_pct = 0.0
        ajuste_unidades = 0.0
        excluir = ajuste3.checkbox(
            "Excluir también la selección",
            key="excluir_seleccion_descartada",
        )
        ajuste1.info("Se sustituye la promoción inferida por la base sin promoción.")
    else:
        ajuste_pct = ajuste1.number_input(
            "Cambio (%)",
            -100.0,
            300.0,
            0.0,
            5.0,
            key="ajuste_pct",
        )
        ajuste_unidades = ajuste2.number_input(
            "Unidades adicionales",
            -1_000_000.0,
            1_000_000.0,
            0.0,
            100.0,
            key="ajuste_unidades",
        )
        excluir = ajuste3.checkbox(
            "Excluir la selección",
            key="excluir_seleccion",
        )

    vista["Pronostico_Seleccionado"] = vista[columna_elegida]
    vista["Pronostico_Ajustado"] = vista["Pronostico_Seleccionado"]
    filas_objetivo = (
        vista["Fecha"].eq(mes_ejemplo)
        if alcance_ajuste == "Sólo el mes seleccionado"
        else pd.Series(True, index=vista.index)
    )

    factor_proteccion = 1.08 if escenario == "Protegido 8%" else 1.0
    if motivo_ajuste == "Reactivación de SKU pausado":
        tabla_reactivacion = tabla_reactivacion.copy()
        tabla_reactivacion["Fecha"] = pd.to_datetime(
            tabla_reactivacion["Fecha"]
        )
        tabla_reactivacion["Demanda_Informada"] = pd.to_numeric(
            tabla_reactivacion["Demanda_Informada"], errors="coerce"
        ).fillna(0.0).clip(lower=0)
        for fila_reactivacion in tabla_reactivacion.itertuples(index=False):
            mascara_mes_reactivado = vista["Fecha"].eq(
                fila_reactivacion.Fecha
            )
            if not mascara_mes_reactivado.any():
                continue
            participaciones = vista.loc[
                mascara_mes_reactivado, "Participacion_Canal_Region"
            ].fillna(0.0)
            total_participaciones = participaciones.sum()
            if total_participaciones > 0:
                pesos_reactivacion = (
                    participaciones / total_participaciones
                )
            else:
                pesos_reactivacion = pd.Series(
                    1 / mascara_mes_reactivado.sum(),
                    index=vista.index[mascara_mes_reactivado],
                )
            vista.loc[
                mascara_mes_reactivado, "Pronostico_Ajustado"
            ] = float(fila_reactivacion.Demanda_Informada) * pesos_reactivacion
        if tabla_reactivacion["Demanda_Informada"].gt(0).any():
            vista["Estado_SKU"] = "Reactivado manualmente"
    elif motivo_ajuste == "Promoción confirmada":
        if usar_factor_historico:
            factores = vista["Factor_Promocional_SKU"].fillna(1.0)
            vista.loc[filas_objetivo, "Pronostico_Ajustado"] = (
                vista.loc[filas_objetivo, "Pronostico_Base"]
                * factores.loc[filas_objetivo]
                * factor_proteccion
            )
        else:
            vista.loc[filas_objetivo, "Pronostico_Ajustado"] = (
                vista.loc[filas_objetivo, "Pronostico_Base"]
                * (1 + ajuste_pct / 100)
                * factor_proteccion
            )
    elif motivo_ajuste == "Promoción descartada":
        vista.loc[filas_objetivo, "Pronostico_Ajustado"] = (
            vista.loc[filas_objetivo, "Pronostico_Base"]
            * factor_proteccion
        )
    else:
        vista.loc[filas_objetivo, "Pronostico_Ajustado"] *= (
            1 + ajuste_pct / 100
        )

    if filas_objetivo.any() and ajuste_unidades:
        total_previo = vista.loc[
            filas_objetivo, "Pronostico_Ajustado"
        ].sum()
        if total_previo > 0:
            pesos = (
                vista.loc[filas_objetivo, "Pronostico_Ajustado"]
                / total_previo
            )
        else:
            pesos = pd.Series(
                1 / filas_objetivo.sum(),
                index=vista.index[filas_objetivo],
            )
        vista.loc[filas_objetivo, "Pronostico_Ajustado"] += (
            ajuste_unidades * pesos
        )
    vista["Pronostico_Ajustado"] = vista["Pronostico_Ajustado"].clip(lower=0)
    if excluir:
        vista.loc[filas_objetivo, "Pronostico_Ajustado"] = 0.0
    vista["Ingreso_Ajustado_USD"] = (
        vista["Pronostico_Ajustado"] * vista["Precio_Venta_USD"]
    )
    vista["Costo_Producto_Ajustado_USD"] = (
        vista["Pronostico_Ajustado"]
        * vista["Costo_Producto_Estimado_USD_Unid"]
    )
    vista["Margen_Bruto_Ajustado_USD"] = (
        vista["Ingreso_Ajustado_USD"]
        - vista["Costo_Producto_Ajustado_USD"]
    )
    comparacion_mensual = vista.groupby("Fecha", as_index=False).agg(
        Sin_Promociones_Futuras=("Pronostico_Base", "sum"),
        Recomendado=("Pronostico_Recomendado", "sum"),
        Protegido=("Pronostico_Protegido", "sum"),
        Seleccion_Ajustada=("Pronostico_Ajustado", "sum"),
    )
    total_elegido = vista["Pronostico_Ajustado"].sum()
    total_central = vista["Pronostico_Recomendado"].sum()
    hist_mascara = pd.Series(True, index=demanda.index)
    if categoria != "Todas": hist_mascara &= demanda["Categoria"].eq(categoria)
    if sku != "Todos": hist_mascara &= demanda["SKU"].eq(sku)
    if canal != "Todos": hist_mascara &= demanda["Canal"].eq(canal)
    if region != "Todas": hist_mascara &= demanda["Region"].eq(region)
    historico_mensual = demanda.loc[hist_mascara].groupby("Fecha", as_index=False).agg(Unidades=("Demanda", "sum")).tail(18)
    ultimos_seis = historico_mensual.tail(6)["Unidades"].sum()
    variacion = (total_elegido / ultimos_seis - 1) * 100 if ultimos_seis else float("nan")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Demanda proyectada · 6 meses", f"{total_elegido:,.0f} unidades")
    p2.metric(
        "Diferencia vs. recomendado · 6 meses",
        f"{total_elegido - total_central:+,.0f} unidades",
    )
    p3.metric("Cambio vs. 6 meses anteriores", f"{variacion:+.1f}%")
    p4.metric(
        "Productos pausados en la selección",
        vista.loc[vista["Estado_SKU"].eq("Pausado"), "SKU"].nunique(),
    )
    st.caption(
        "Estos indicadores suman la demanda en unidades de los seis meses "
        "proyectados y respetan los filtros seleccionados."
    )

    st.subheader("Resumen de la proyección seleccionada")
    if sku != "Todos":
        productos = vista["Producto"].dropna().unique()
        producto = f" ({productos[0]})" if len(productos) else ""
        alcance_producto = f"del SKU {sku}{producto}"
    elif categoria != "Todas":
        alcance_producto = f"de la categoría {categoria}"
    else:
        alcance_producto = "de todos los productos"

    alcance_region = (
        f"en la región {region}"
        if region != "Todas"
        else "en todas las regiones"
    )
    alcance_canal = (
        f"por el canal {canal}"
        if canal != "Todos"
        else "sumando todos los canales"
    )
    nombres_modelo = {
        "Sin promociones futuras": (
            "pronóstico de promedio reciente y temporada, sin promociones futuras"
        ),
        "Recomendado": (
            "modelo final de promedio reciente, estacionalidad y promociones recurrentes"
            if es_caso_validado
            else "método recalculado de promedio reciente, estacionalidad y promociones recurrentes"
        ),
        "Protegido 8%": (
            "escenario protegido del modelo final, con un colchón de 8%"
        ),
    }
    nombre_metodo_mostrado = (
        "dato informado para reactivar el SKU pausado"
        if motivo_ajuste == "Reactivación de SKU pausado"
        else nombres_modelo[escenario]
    )
    st.success(
        f"Con el **{nombre_metodo_mostrado}**, se proyecta que la demanda "
        f"**{alcance_producto} {alcance_canal} {alcance_region}** será de "
        f"aproximadamente **{total_elegido:,.0f} unidades durante "
        f"{periodo_pronostico}**, considerando "
        f"{comparacion_mensual['Fecha'].nunique()} meses."
    )
    resumen_meses = comparacion_mensual[["Fecha", "Seleccion_Ajustada"]].copy()
    resumen_meses["Mes"] = resumen_meses["Fecha"].apply(
        lambda fecha: (
            f"{meses_es[pd.Timestamp(fecha).month].capitalize()} "
            f"{pd.Timestamp(fecha).year}"
        )
    )
    detalle_meses_texto = " · ".join(
        f"{fila.Mes}: {fila.Seleccion_Ajustada:,.0f}"
        for fila in resumen_meses.itertuples(index=False)
    )
    st.markdown(f"**Mes por mes, en unidades:** {detalle_meses_texto}")
    st.caption(
        "El total y cada mes se recalculan automáticamente con la categoría, "
        "producto, canal, región, escenario y ajustes seleccionados arriba."
    )

    st.subheader("Comparación mensual de escenarios")
    comparacion_larga = comparacion_mensual.rename(
        columns={"Sin_Promociones_Futuras": "Sin promociones futuras"}
    ).melt(
        "Fecha",
        value_vars=["Sin promociones futuras", "Recomendado", "Protegido"],
        var_name="Escenario",
        value_name="Unidades",
    )
    figura_escenarios = px.line(
        comparacion_larga,
        x="Fecha",
        y="Unidades",
        color="Escenario",
        markers=True,
    )
    eje_meses_espanol(figura_escenarios, comparacion_larga["Fecha"])
    st.plotly_chart(
        figura_escenarios,
        width="stretch",
        key="pronostico_escenarios",
    )
    tabla_comparacion_mensual = comparacion_mensual.rename(
        columns={
            "Sin_Promociones_Futuras": "Sin promociones futuras",
            "Seleccion_Ajustada": "Selección después del ajuste",
        }
    )
    st.dataframe(
        tabla_comparacion_mensual.style.format(
            {
                "Sin promociones futuras": "{:,.0f}",
                "Recomendado": "{:,.0f}",
                "Protegido": "{:,.0f}",
                "Selección después del ajuste": "{:,.0f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Historia frente a la selección ajustada")
    historia = historico_mensual.rename(columns={"Unidades": "Valor"}).assign(Serie="Histórico")
    futuro_grafica = comparacion_mensual[["Fecha", "Seleccion_Ajustada"]].rename(columns={"Seleccion_Ajustada": "Valor"}).assign(Serie=f"{escenario} ajustado")
    historia_completa = pd.concat([historia, futuro_grafica])
    figura_historia = px.line(
        historia_completa,
        x="Fecha",
        y="Valor",
        color="Serie",
        markers=True,
    )
    eje_meses_espanol(figura_historia, historia_completa["Fecha"])
    st.plotly_chart(
        figura_historia,
        width="stretch",
        key="historia_seleccion",
    )
    panel_desgloses = st.expander("Ver pronóstico por categoría, canal y región")
    graf1, graf2, graf3 = panel_desgloses.columns(3)
    por_categoria = vista.groupby("Categoria", as_index=False).agg(Unidades=("Pronostico_Ajustado", "sum"))
    por_canal = vista.groupby("Canal", as_index=False).agg(Unidades=("Pronostico_Ajustado", "sum"))
    por_region = vista.groupby("Region", as_index=False).agg(Unidades=("Pronostico_Ajustado", "sum"))
    graf1.plotly_chart(px.bar(por_categoria, x="Categoria", y="Unidades", text_auto=".3s"), width="stretch", key="grafico_categoria")
    graf2.plotly_chart(px.bar(por_canal, x="Canal", y="Unidades", text_auto=".3s"), width="stretch", key="grafico_canal")
    graf3.plotly_chart(px.bar(por_region, x="Region", y="Unidades", text_auto=".3s"), width="stretch", key="grafico_region")
    with st.expander("Ver y descargar detalle"):
        columnas = [
            "Fecha", "SKU", "Producto", "Categoria", "Canal", "Region",
            "Estado_SKU", "Participacion_Canal_Region", "Metodo_Reparto",
            "Pronostico_Base", "Pronostico_Recomendado",
            "Pronostico_Protegido", "Pronostico_Ajustado",
            "Precio_Venta_USD", "Costo_Producto_Estimado_USD_Unid",
            "Margen_Bruto_pct", "Ingreso_Ajustado_USD",
            "Costo_Producto_Ajustado_USD", "Margen_Bruto_Ajustado_USD",
            "Costo_Almacenaje_Mes_USD_Unid", "Vida_Util_Meses",
        ]
        detalle = vista[columnas].sort_values(["Fecha", "SKU", "Canal", "Region"])
        usos_respaldo = detalle["Metodo_Reparto"].eq(
            "Participación histórica general del SKU"
        ).sum()
        if usos_respaldo:
            st.caption(
                f"En {usos_respaldo:,} filas se utilizó la participación histórica "
                "general porque esa combinación canal-región todavía no tenía "
                "historia para el mismo mes calendario."
            )
        st.dataframe(detalle, width="stretch", hide_index=True)
        st.download_button("Descargar resultado ajustado", data=descargar_excel(detalle), file_name="pronostico_ajustado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab_robustez:
    st.header("Dónde funciona el 8% y dónde deja de funcionar")
    if robustez is None:
        st.info("Un archivo nuevo necesita su propia validación histórica; no se reutilizan métricas del caso original.")
    else:
        tabla_global = robustez["Categoría"]
        error_rec = promedio_ponderado(tabla_global, "WAPE_Recomendado_pct")
        error_prot = promedio_ponderado(tabla_global, "WAPE_Protegido_pct")
        sub_rec = promedio_ponderado(tabla_global, "Subestimacion_Recomendado_pct")
        sub_prot = promedio_ponderado(tabla_global, "Subestimacion_Protegido_pct")
        sobre_rec = promedio_ponderado(tabla_global, "Sobreestimacion_Recomendado_pct")
        sobre_prot = promedio_ponderado(tabla_global, "Sobreestimacion_Protegido_pct")
        rb1, rb2, rb3, rb4 = st.columns(4)
        cantidad_mejoran = int(tabla_global["Proteccion_Mejora_WAPE"].sum())
        rb1.metric("Error total", f"{error_rec:.2f} → {error_prot:.2f} por cada 100")
        rb2.metric("Faltante pronosticado", f"{sub_rec:.2f}% → {sub_prot:.2f}%")
        rb3.metric("Exceso pronosticado", f"{sobre_rec:.2f}% → {sobre_prot:.2f}%")
        rb4.metric(
            "Segmentos donde baja el error",
            f"{cantidad_mejoran} de {len(tabla_global)}",
        )
        st.write(
            "El colchón reduce los faltantes, pero puede elevar el error total al "
            "crear más excedente. Por eso no reemplaza automáticamente al escenario recomendado."
        )
        tipo = st.radio("Ver resultados por", ["SKU", "Categoría", "Mes"], horizontal=True, key="robustez_tipo")
        tabla = robustez[tipo].copy()
        if tipo == "SKU": tabla["Segmento"] = tabla["SKU"] + " · " + tabla["Producto"]
        elif tipo == "Categoría": tabla["Segmento"] = tabla["Categoria"]
        else:
            meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
            tabla["Segmento"] = tabla["Mes_Calendario"].map(meses)
        tabla["Resultado"] = tabla["Proteccion_Mejora_WAPE"].map(
            {True: "Reduce el error total", False: "Aumenta el error total"}
        )
        dispersion = px.scatter(
            tabla,
            x="WAPE_Recomendado_pct",
            y="WAPE_Protegido_pct",
            size="Demanda_Real",
            color="Resultado",
            hover_name="Segmento",
            color_discrete_map={
                "Reduce el error total": "#2ca02c",
                "Aumenta el error total": "#d62728",
            },
            labels={
                "WAPE_Recomendado_pct": "Error del escenario recomendado por cada 100 unidades reales",
                "WAPE_Protegido_pct": "Error del escenario protegido por cada 100 unidades reales",
                "Demanda_Real": "Demanda real",
            },
        )
        minimo = min(tabla["WAPE_Recomendado_pct"].min(), tabla["WAPE_Protegido_pct"].min())
        maximo = max(tabla["WAPE_Recomendado_pct"].max(), tabla["WAPE_Protegido_pct"].max())
        dispersion.add_shape(type="line", x0=minimo, y0=minimo, x1=maximo, y1=maximo, line={"color": "gray", "dash": "dash"})
        st.plotly_chart(dispersion, width="stretch", key="robustez_dispersion")
        st.caption(
            "Debajo de la diagonal, el colchón de 8% reduce el error total. "
            "Encima de la diagonal puede reducir faltantes, pero crea suficiente "
            "exceso para aumentar el error total."
        )
        columnas = ["Segmento", "Demanda_Real", "WAPE_Recomendado_pct", "WAPE_Protegido_pct", "Cambio_WAPE_pct", "Sesgo_Protegido_pct", "Subestimacion_Recomendado_pct", "Subestimacion_Protegido_pct", "Sobreestimacion_Protegido_pct", "Resultado"]
        tabla_mostrada = tabla[columnas].sort_values(
            "WAPE_Protegido_pct", ascending=False
        ).rename(
            columns={
                "Demanda_Real": "Demanda real",
                "WAPE_Recomendado_pct": "Error recomendado por cada 100",
                "WAPE_Protegido_pct": "Error protegido por cada 100",
                "Cambio_WAPE_pct": "Cambio del error",
                "Sesgo_Protegido_pct": "Balance neto protegido (%)",
                "Subestimacion_Recomendado_pct": "Faltante recomendado (%)",
                "Subestimacion_Protegido_pct": "Faltante protegido (%)",
                "Sobreestimacion_Protegido_pct": "Exceso protegido (%)",
            }
        )
        st.dataframe(
            tabla_mostrada.style.format(
                {
                    "Demanda real": "{:,.0f}",
                    "Error recomendado por cada 100": "{:.2f}",
                    "Error protegido por cada 100": "{:.2f}",
                    "Cambio del error": "{:+.2f}",
                    "Balance neto protegido (%)": "{:+.2f}%",
                    "Faltante recomendado (%)": "{:.2f}%",
                    "Faltante protegido (%)": "{:.2f}%",
                    "Exceso protegido (%)": "{:.2f}%",
                }
            ),
            width="stretch",
            hide_index=True,
        )

with tab_detalle:
    st.header("Un SKU y un mes, modelo por modelo")
    st.write(
        "Esta sección baja del error total a una predicción concreta. El error "
        "se calcula como `pronóstico - venta real para modelar`: negativo "
        "significa que el "
        "modelo quedó corto y positivo que proyectó de más."
    )
    if detalle_modelos is None:
        st.info(
            "El archivo nuevo todavía no tiene una validación histórica propia. "
            "Hay que ejecutar el backtest antes de comparar errores por fila."
        )
    else:
        vista_detalle = st.radio(
            "Qué quieres revisar",
            ["Validación 2025", "Pronóstico 2026"],
            horizontal=True,
            key="tipo_detalle_modelos",
        )

        if vista_detalle == "Validación 2025":
            validacion = detalle_modelos["Validación 2025"].copy()
            validacion["Fecha"] = pd.to_datetime(validacion["Fecha"])
            d1, d2, d3 = st.columns(3)
            categorias_detalle = sorted(validacion["Categoria"].unique())
            categoria_detalle = d1.selectbox(
                "Categoría",
                categorias_detalle,
                index=(
                    categorias_detalle.index("Lacteos")
                    if "Lacteos" in categorias_detalle
                    else 0
                ),
                key="detalle_categoria_2025",
            )
            opciones_sku = sorted(
                validacion.loc[
                    validacion["Categoria"].eq(categoria_detalle), "SKU"
                ].unique()
            )
            sku_detalle = d2.selectbox(
                "SKU",
                opciones_sku,
                index=(
                    opciones_sku.index("SKU-1001")
                    if "SKU-1001" in opciones_sku
                    else 0
                ),
                key="detalle_sku_2025",
            )
            fechas_detalle = sorted(
                validacion.loc[
                    validacion["SKU"].eq(sku_detalle), "Fecha"
                ].unique()
            )
            fecha_objetivo = pd.Timestamp("2025-03-01")
            indice_fecha = (
                fechas_detalle.index(fecha_objetivo)
                if fecha_objetivo in fechas_detalle
                else 0
            )
            fecha_detalle = d3.selectbox(
                "Mes evaluado",
                fechas_detalle,
                index=indice_fecha,
                format_func=lambda fecha: pd.Timestamp(fecha).strftime("%Y-%m"),
                key="detalle_fecha_2025",
            )
            fila = validacion.loc[
                validacion["SKU"].eq(sku_detalle)
                & validacion["Fecha"].eq(fecha_detalle)
            ].iloc[0]

            modelos_fila = [
                ("Pronóstico entregado por la empresa", "Pronostico_Empresa", "Error_Empresa", "Error_pct_Empresa"),
                ("Mismo mes anterior", "Pronostico_Mismo_Mes_Anterior", "Error_Mismo_Mes_Anterior", "Error_pct_Mismo_Mes_Anterior"),
                ("Promedio reciente + estacionalidad", "Pronostico_Ponderado_Estacional", "Error_Ponderado_Estacional", "Error_pct_Ponderado_Estacional"),
                ("Modelo final recomendado", "Pronostico_Recomendado", "Error_Recomendado", "Error_pct_Recomendado"),
                ("Modelo final + protección 8%", "Pronostico_Protegido", "Error_Protegido", "Error_pct_Protegido"),
            ]
            comparacion_fila = []
            for modelo, columna_pronostico, columna_error, columna_pct in modelos_fila:
                error = fila[columna_error]
                comparacion_fila.append(
                    {
                        "Modelo": modelo,
                        "Venta_Real_Modelo": fila["Venta_Real"],
                        "Pronostico": fila[columna_pronostico],
                        "Error_Unidades": error,
                        "Error_Absoluto": abs(error),
                        "Error_pct": fila[columna_pct],
                        "Resultado": (
                            "Sobreestimó" if error > 0
                            else "Subestimó" if error < 0
                            else "Exacto"
                        ),
                    }
                )
            comparacion_fila = pd.DataFrame(comparacion_fila)
            mejor_modelo = comparacion_fila.sort_values(
                "Error_Absoluto"
            ).iloc[0]

            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Venta real para modelar", f"{fila['Venta_Real']:,.2f}")
            e2.metric("Modelo más cercano", mejor_modelo["Modelo"])
            e3.metric("Menor error absoluto", f"{mejor_modelo['Error_Absoluto']:,.2f}")
            e4.metric(
                "Promoción recurrente esperada",
                f"{fila['Proporcion_Promocion_Esperada']:.1%}",
            )

            grafica_fila = pd.concat(
                [
                    pd.DataFrame(
                        [{"Modelo": "Venta real", "Valor": fila["Venta_Real"]}]
                    ),
                    comparacion_fila[["Modelo", "Pronostico"]].rename(
                        columns={"Pronostico": "Valor"}
                    ),
                ],
                ignore_index=True,
            )
            st.plotly_chart(
                px.bar(
                    grafica_fila,
                    x="Modelo",
                    y="Valor",
                    color="Modelo",
                    text_auto=".4s",
                    title=(
                        f"{fila['Producto']} · "
                        f"{pd.Timestamp(fecha_detalle):%Y-%m}"
                    ),
                ),
                width="stretch",
                key="detalle_validacion_grafica",
            )
            st.dataframe(
                comparacion_fila.style.format(
                    {
                        "Venta_Real_Modelo": "{:,.2f}",
                        "Pronostico": "{:,.2f}",
                        "Error_Unidades": "{:+,.2f}",
                        "Error_Absoluto": "{:,.2f}",
                        "Error_pct": "{:+.2f}%",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Esta comparación no elige un modelo usando un solo mes. Sirve "
                "para explicar cómo se comportó cada alternativa dentro del "
                "backtest completo."
            )
            st.download_button(
                "Descargar las 294 comparaciones de 2025",
                data=descargar_excel(validacion),
                file_name="detalle_validacion_modelos_2025.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="descargar_detalle_2025",
            )

        else:
            trazabilidad = detalle_modelos["Pronóstico 2026"].copy()
            trazabilidad["Fecha"] = pd.to_datetime(trazabilidad["Fecha"])
            t1, t2, t3 = st.columns(3)
            categorias_traza = sorted(trazabilidad["Categoria"].unique())
            categoria_traza = t1.selectbox(
                "Categoría",
                categorias_traza,
                index=(
                    categorias_traza.index("Lacteos")
                    if "Lacteos" in categorias_traza
                    else 0
                ),
                key="traza_categoria_2026",
            )
            opciones_sku_traza = sorted(
                trazabilidad.loc[
                    trazabilidad["Categoria"].eq(categoria_traza), "SKU"
                ].unique()
            )
            sku_traza = t2.selectbox(
                "SKU",
                opciones_sku_traza,
                index=(
                    opciones_sku_traza.index("SKU-1001")
                    if "SKU-1001" in opciones_sku_traza
                    else 0
                ),
                key="traza_sku_2026",
            )
            fechas_traza = sorted(
                trazabilidad.loc[
                    trazabilidad["SKU"].eq(sku_traza), "Fecha"
                ].unique()
            )
            fecha_traza_objetivo = pd.Timestamp("2026-03-01")
            indice_traza = (
                fechas_traza.index(fecha_traza_objetivo)
                if fecha_traza_objetivo in fechas_traza
                else 0
            )
            fecha_traza = t3.selectbox(
                "Mes proyectado",
                fechas_traza,
                index=indice_traza,
                format_func=lambda fecha: pd.Timestamp(fecha).strftime("%Y-%m"),
                key="traza_fecha_2026",
            )
            fila_traza = trazabilidad.loc[
                trazabilidad["SKU"].eq(sku_traza)
                & trazabilidad["Fecha"].eq(fecha_traza)
            ].iloc[0]

            recorrido = pd.DataFrame(
                [
                    ["Venta del mismo mes 2023", fila_traza["Venta_Mismo_Mes_2023"]],
                    ["Venta del mismo mes 2024", fila_traza["Venta_Mismo_Mes_2024"]],
                    ["Venta del mismo mes 2025", fila_traza["Venta_Mismo_Mes_2025"]],
                    ["Sin promociones futuras 2026", fila_traza["Pronostico_Modelo_Sin_Promocion"]],
                    ["Recomendado 2026", fila_traza["Pronostico_Recomendado"]],
                    ["Protegido 8% 2026", fila_traza["Pronostico_Protegido"]],
                ],
                columns=["Referencia", "Unidades"],
            )
            promo_incremento = (
                fila_traza["Pronostico_Recomendado"]
                - fila_traza["Pronostico_Modelo_Sin_Promocion"]
            )
            proteccion_incremento = (
                fila_traza["Pronostico_Protegido"]
                - fila_traza["Pronostico_Recomendado"]
            )
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Recomendado 2026", f"{fila_traza['Pronostico_Recomendado']:,.2f}")
            q2.metric("Efecto promocional", f"{promo_incremento:+,.2f}")
            q3.metric("Colchón protegido", f"{proteccion_incremento:+,.2f}")
            q4.metric(
                "Vs. mismo mes 2025",
                f"{fila_traza['Variacion_Recomendado_vs_2025_pct']:+.1f}%",
            )
            st.plotly_chart(
                px.bar(
                    recorrido,
                    x="Referencia",
                    y="Unidades",
                    color="Referencia",
                    text_auto=".4s",
                    title=(
                        f"{fila_traza['Producto']} · "
                        f"{pd.Timestamp(fecha_traza):%Y-%m}"
                    ),
                ),
                width="stretch",
                key="trazabilidad_2026_grafica",
            )
            st.dataframe(
                recorrido.style.format({"Unidades": "{:,.2f}"}),
                width="stretch",
                hide_index=True,
            )
            st.write(
                f"**Estado del SKU:** {fila_traza['Estado_SKU']}. "
                f"**Promoción recurrente:** "
                f"{'sí' if fila_traza['Promocion_Recurrente'] else 'no'}. "
                f"**Proporción promocional esperada:** "
                f"{fila_traza['Proporcion_Promocion_Esperada']:.1%}."
            )
            st.caption(
                "Los tres años anteriores son contexto, no una fórmula directa. "
                "La base también utiliza el promedio de los dos meses comparables "
                "más recientes, después de retirar el efecto estacional."
            )
            st.download_button(
                "Descargar la trazabilidad completa de 2026",
                data=descargar_excel(trazabilidad),
                file_name="trazabilidad_pronostico_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="descargar_trazabilidad_2026",
            )

with tab_notas:
    st.header("Decisiones, supuestos y preguntas que deben decirse en voz alta")
    nota1, nota2 = st.columns(2)
    with nota1:
        st.subheader("Decisiones respaldadas por los datos")
        st.markdown("- Conservar siempre los valores originales.\n- Modelar negativos como cero porque así reconcilian.\n- Completar precios con catálogo.\n- Pronosticar por SKU y distribuir regiones después.\n- Mantener Azúcar en pausa hasta confirmación.\n- Usar recurrencia si no hay calendario.\n- Mostrar recomendado y protegido por separado.")
    with nota2:
        st.subheader("Supuestos y limitaciones")
        st.markdown("- Promoción no informa duración, descuento ni tipo.\n- Las 28 unidades vacías son estimaciones.\n- La pausa de Azúcar es una inferencia.\n- No se conoce la antigüedad ni el lote del inventario.\n- No se reprodujeron el 96% ni la rotación 5.1.\n- Hay USD 946,107 gerenciales no explicados por regiones.")
    st.subheader("Ideas que surgieron y todavía pueden probarse")
    st.markdown("- Usar un calendario de promociones si se recibe.\n- Aplicar protección sólo a SKU donde el pronóstico tienda a quedar corto.\n- Crear más cortes históricos recalculando promociones.\n- Simular más datos faltantes.\n- Convertir protección en política de inventario con costos.\n- Reactivar Azúcar con control manual.")
    st.subheader("Resumen corto para presentar")
    st.info("Conservé el dato original y construí una versión trazable. Probé alternativas antes de elegir un modelo por SKU con promedio reciente, estacionalidad y promociones recurrentes. Por cada 100 unidades reales, acumuló 10.56 unidades de error, frente a 19.22 del pronóstico entregado por la empresa. Separé esa estimación de un escenario protegido con 8%, porque reducir faltantes es una decisión de riesgo y no debe ocultarse dentro del pronóstico.")

st.caption("Caso reproducible: datos originales, decisiones, validaciones, modelos descartados, pronóstico recomendado y escenarios de riesgo.")
