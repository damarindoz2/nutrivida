"""Primera revisión del archivo Datos_NutriVida.xlsx.

Este programa sólo lee el Excel: no modifica ninguna hoja.
Ejecutarlo desde la carpeta principal con:

    .venv/bin/python 01_revision_inicial.py
"""

from pathlib import Path

import pandas as pd


# __file__ es la ubicación de este programa. Así encontramos el Excel aunque
# el comando se ejecute desde otra carpeta.
ARCHIVO = Path(__file__).with_name("Datos_NutriVida.xlsx")

# sheet_name=None significa: "leer todas las hojas".
# El resultado es un diccionario: nombre de hoja -> tabla (DataFrame).
hojas = pd.read_excel(ARCHIVO, sheet_name=None)

print("1. TAMAÑO DE CADA HOJA")
for nombre, tabla in hojas.items():
    filas, columnas = tabla.shape
    print(f"- {nombre}: {filas:,} filas x {columnas} columnas")


ventas = hojas["Ventas Historicas"].copy()
pronostico = hojas["Pronostico vs Real"].copy()
resumen = hojas["Resumen Gerencia"].copy()

print("\n2. PROBLEMAS BÁSICOS EN VENTAS")
print("- Filas idénticas duplicadas:", ventas.duplicated().sum())
print("- Unidades vacías:", ventas["Unidades"].isna().sum())
print("- Precios vacíos:", ventas["Precio_Unitario_USD"].isna().sum())
print("- Unidades negativas:", ventas["Unidades"].lt(0).sum())
print("- Unidades en cero:", ventas["Unidades"].eq(0).sum())

print("\n3. NOMBRES USADOS PARA EL CANAL")
print(ventas["Canal"].value_counts().to_string())

# errors="coerce" convierte cualquier fecha inválida en un valor vacío (NaT).
fechas = pd.to_datetime(ventas["Fecha"], format="%Y-%m", errors="coerce")
print("\n4. PERÍODO DISPONIBLE")
print(f"- Desde: {fechas.min():%Y-%m}")
print(f"- Hasta: {fechas.max():%Y-%m}")
print("- Meses distintos:", fechas.nunique())
print("- Fechas inválidas:", fechas.isna().sum())

# Agrupamos las nueve combinaciones de canal y región para obtener una venta
# mensual por producto y poder compararla con la hoja Pronóstico vs Real.
venta_por_sku_mes = (
    ventas.groupby(["Fecha", "SKU"], as_index=False)["Unidades"]
    .sum()
    .rename(columns={"Unidades": "Suma_Detalle"})
)
comparacion = pronostico.merge(venta_por_sku_mes, on=["Fecha", "SKU"], how="left")
comparacion["Diferencia"] = (
    comparacion["Venta_Real"] - comparacion["Suma_Detalle"]
)
diferencias = comparacion.loc[comparacion["Diferencia"].ne(0)]

print("\n5. CONSISTENCIA ENTRE HOJAS")
print("- SKU-meses comparados:", len(comparacion))
print("- SKU-meses con diferencia:", len(diferencias))
print(
    diferencias[["Fecha", "SKU", "Venta_Real", "Suma_Detalle", "Diferencia"]]
    .to_string(index=False)
)

# Para expresar ventas en dólares multiplicamos unidades por precio unitario.
ventas["Fecha_dt"] = fechas
ventas["Venta_USD"] = ventas["Unidades"] * ventas["Precio_Unitario_USD"]
ventas_2025 = ventas.loc[ventas["Fecha_dt"].dt.year.eq(2025)]
total_calculado = ventas_2025["Venta_USD"].sum()
regiones_calculadas = ventas_2025.groupby("Region")["Venta_USD"].sum()

print("\n6. VENTAS 2025: CÁLCULO VS. RESUMEN GERENCIAL")
print(f"- Total calculado desde el detalle: USD {total_calculado:,.2f}")
print("- Cálculo por región:")
print(regiones_calculadas.map(lambda valor: f"USD {valor:,.2f}").to_string())
print("- Valores que aparecen en Resumen Gerencia:")
print(resumen.iloc[:4].to_string(index=False))
