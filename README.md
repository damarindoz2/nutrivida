# NutriVida · pronóstico de demanda

Solución reproducible para analizar, limpiar y proyectar seis meses de demanda
a partir de un Excel con ventas mensuales. El proyecto conserva los datos
originales, documenta cada decisión y presenta los resultados mediante un
dashboard.

> NutriVida es una empresa ficticia y los datos del caso son sintéticos.

## Resultado principal

Se comparó el pronóstico entregado por la empresa contra distintas alternativas
mediante dos periodos históricos de prueba de seis meses. El método recomendado
combina el promedio de los dos meses comparables más recientes, estacionalidad
y promociones recurrentes.

| Alternativa | Error acumulado por cada 100 unidades reales | Balance neto |
|---|---:|---:|
| Pronóstico entregado por la empresa | 19.22 | +7.69% |
| Modelo recomendado | **10.56** | -5.35% |
| Escenario protegido con 8% adicional | 10.61 | +2.22% |

El error acumulado suma las diferencias absolutas y las compara contra la
demanda real. Por ejemplo, 10.56 significa que por cada 100 unidades reales el
pronóstico acumuló aproximadamente 10.56 unidades de diferencia. El balance
neto negativo indica que, al sumar todo, el modelo tendió a quedarse corto.

El pronóstico recomendado para enero-junio de 2026 es de **1,224,820 unidades**.
El escenario protegido suma **1,322,806 unidades**; se presenta aparte porque
reduce faltantes a cambio de mayor riesgo de excedente.

## Qué se encontró en los datos

La hoja de ventas tenía 8,114 filas. Después de revisar cada problema:

- se retiraron 14 copias exactas y quedaron 8,100 claves válidas;
- se homologaron variantes evidentes de Ecommerce y Supermercado sin mezclar
  ambos canales;
- 19 precios vacíos se completaron con el catálogo, después de comprobar que
  coincidía con las referencias observadas;
- 9 unidades negativas se trataron como cero para modelar porque así
  reconciliaban con las ventas consolidadas;
- 28 unidades vacías se conservaron en la columna original y se estimaron en
  `Unidades_Modelo` mediante referencias temporales y estacionales;
- un valor extremo de 13,380 unidades se conservó en el original y se sustituyó
  sólo para modelar por una estimación de 1,533.25;
- seis meses completos en cero de `SKU-1021` se interpretaron como una pausa,
  no como una descontinuación definitiva;
- la promoción sólo informa 0/1, por lo que no se inventaron descuentos,
  duración ni tipo de campaña.

Las decisiones completas están en
[DECISIONES_ANALISIS.md](DECISIONES_ANALISIS.md) y el recorrido de limpieza en
[BITACORA_LIMPIEZA.md](BITACORA_LIMPIEZA.md).

## Cómo funciona el método recomendado

1. Se estima la demanda normal sin el efecto de promociones históricas.
2. Se calcula qué meses suelen estar por encima o debajo del promedio de cada
   SKU.
3. Se promedian los dos meses comparables más recientes. También se probó un
   tercer mes, pero la validación histórica le asignó peso cero.
4. Se recupera el efecto estacional del mes que se desea pronosticar.
5. Se incorpora una promoción sólo cuando el mismo SKU y mes la tuvieron en al
   menos dos años conocidos.
6. El total mensual del SKU se distribuye entre canal y región sin cambiar su
   suma.

Si se recibe un calendario de promociones futuras, éste debe sustituir la
inferencia de recurrencia. El escenario protegido agrega 8% al recomendado como
decisión de riesgo; no se presenta como una predicción más probable. Se probaron
incrementos de 0%, 2%, 4%, 6%, 8% y 10% en enero-junio de 2025: el 8% dejó el
balance neto más cerca de cero y después se validó sin modificarlo en el segundo
semestre.

## Formas de revisar el proyecto

### 1. Resumen técnico reproducible

[Abrir el notebook del análisis](notebooks/recorrido_analisis.ipynb). GitHub lo
muestra directamente con las tablas y gráficas ya ejecutadas.

### 2. Dashboard interactivo

Permite cargar otro Excel, volver a ejecutar la limpieza, recalcular una
validación histórica, proyectar los seis meses siguientes, filtrar resultados y
aplicar cambios manuales visibles.

```bash
streamlit run dashboard.py
```

### 3. Resultado tabular

[Pronostico_NutriVida_2026_FINAL.xlsx](resultados/Pronostico_NutriVida_2026_FINAL.xlsx)
contiene el pronóstico, sus desgloses, las pruebas históricas y la trazabilidad.
Las copias CSV están en [`resultados/respaldos_csv/`](resultados/respaldos_csv/).

## Instalación

Requiere Python 3.11 o posterior.

```bash
git clone https://github.com/damarindoz2/nutrivida.git
cd nutrivida
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Windows, la activación del entorno es:

```powershell
.venv\Scripts\Activate.ps1
```

Para abrir el notebook:

```bash
jupyter lab
```

## Estructura

```text
dashboard.py                 interfaz y explicación visual
limpieza_datos.py            validación y reglas de limpieza
modelo_demanda.py            estacionalidad, promociones y pronóstico
flujo_analisis.py            conexión entre limpieza, validación y modelo
mi_analisis.py               bitácora reproducible del caso original
notebooks/                   recorrido técnico ejecutado
resultados/                  Excel final, CSV y versión inicial archivada
```

El mapa detallado para saber qué archivo modificar está en
[ESTRUCTURA_CODIGO.md](ESTRUCTURA_CODIGO.md).

## Supuestos y limitaciones

- La venta perdida se interpreta como demanda no atendida porque sólo aparece
  cuando el stock llega a cero.
- No se conoce la edad de los lotes; la vida útil no basta para calcular merma.
- El indicador de servicio declarado de 96% y la rotación de 5.1 no pudieron
  reproducirse con una fórmula inequívoca.
- Precio y margen permiten traducir unidades a dinero, pero no cambian la
  demanda sin información de elasticidad.
- El resultado de 2026 todavía no existe; la calidad esperada proviene de
  periodos históricos ocultados al modelo.

## Documentación adicional

- [Modelos probados](MODELOS_PROBADOS.md)
- [Descripción de los resultados](resultados/LEEME_RESULTADOS.md)
