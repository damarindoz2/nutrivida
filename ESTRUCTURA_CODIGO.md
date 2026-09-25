# Mapa del código

El proyecto operativo está separado para que cada tipo de cambio tenga un lugar
claro. El dashboard no contiene las reglas de limpieza ni las fórmulas del
pronóstico: las importa desde módulos especializados.

## Qué archivo abrir según lo que te pidan

| Si necesitas cambiar... | Abre | Busca |
|---|---|---|
| Columnas obligatorias del Excel | `limpieza_datos.py` | `HOJAS_REQUERIDAS` |
| Equivalencias de canales o regiones | `limpieza_datos.py` | `CANAL_CANONICO` o `REGION_CANONICA` |
| Tratamiento de duplicados, negativos o precios vacíos | `limpieza_datos.py` | `limpiar_tablas_nuevas` |
| Estimación de unidades vacías | `limpieza_datos.py` | comentario “Si el vacío...” |
| Detección de valores atípicos | `limpieza_datos.py` | comentario “Ajuste conservador...” |
| Reconciliación con inventario y ventas consolidadas | `limpieza_datos.py` | `auditar_reconciliacion_ventas` |
| Promedio de los dos meses comparables más recientes | `modelo_demanda.py` | columna `Peso` dentro de `pronostico_preliminar` |
| Estacionalidad | `modelo_demanda.py` | `Indice_Estacional` |
| Promociones recurrentes | `modelo_demanda.py` | `Proporcion_Promocion_Esperada` |
| Colchón protegido de 8% | `modelo_demanda.py` | `Pronostico_Protegido` |
| Pausa de un SKU | `modelo_demanda.py` | comentario “Marcar pausas...” |
| Reparto por canal y región | `modelo_demanda.py` | comentario “Repartir el total...” |
| Meses reservados para validar el modelo | `flujo_analisis.py` | comentario “Validación automática...” |
| Orden de cargar, limpiar, modelar y validar | `flujo_analisis.py` | `ejecutar_flujo_analisis` |
| Texto, filtros, tablas o gráficas | `dashboard.py` | nombre visible de la sección |

## Cómo se conectan

```text
Excel nuevo
    ↓
limpieza_datos.py
    ↓ ventas limpias + diagnóstico
modelo_demanda.py
    ↓ pronóstico y validación histórica
flujo_analisis.py
    ↓ reúne todos los resultados
dashboard.py
    ↓ explica y permite interactuar
Usuario
```

## Responsabilidad de cada archivo

### `limpieza_datos.py`

Valida la plantilla y prepara los datos. Conserva las unidades originales y
crea `Unidades_Modelo` para los valores estimados o ajustados. También comprueba
si las hojas consolidadas coinciden con el detalle.

### `modelo_demanda.py`

Contiene el cálculo de demanda: promedio reciente comparable, estacionalidad, efecto
promocional, recurrencia, escenario protegido y distribución por canal-región.
No contiene componentes visuales.

### `flujo_analisis.py`

Coordina el proceso completo. Decide si debe abrir el caso precalculado o
procesar un Excel nuevo. Para una fuente nueva también oculta sus últimos seis
meses y compara la proyección con lo que realmente ocurrió.

### `dashboard.py`

Sólo se ocupa de la presentación: carga del archivo, filtros, explicaciones,
gráficas, ajustes manuales y descargas. Tiene una función pequeña llamada
`cargar_datos` únicamente para guardar el resultado en memoria y evitar repetir
el proceso en cada clic.

### `mi_analisis.py`

Es la bitácora exploratoria con la que se investigó el caso original y se
generaron los archivos precalculados. No es importada por el dashboard y no es
el archivo que debes modificar durante el uso normal. Se conserva
como evidencia del recorrido analítico y para regenerar la entrega original.
Los archivos que genera se guardan dentro de `resultados/`: el libro oficial en
la raíz de esa carpeta, los CSV en `respaldos_csv/` y la primera versión en
`versiones_anteriores/`.

## Reglas para modificar sin romper el proyecto

1. Cambia la regla en un solo módulo; no copies la fórmula al dashboard.
2. Conserva los nombres de las columnas que salen de cada función.
3. Después de un cambio ejecuta las comprobaciones rápidas:

```bash
../.venv/bin/python -m py_compile dashboard.py limpieza_datos.py modelo_demanda.py flujo_analisis.py
../.venv/bin/streamlit run dashboard.py
```

4. Prueba también un Excel cargado, porque el caso original utiliza resultados
   precalculados y un archivo nuevo recorre todo el proceso desde cero.

## Ejemplos rápidos

- “Cambia el 8% a 5%”: abre `modelo_demanda.py` y cambia `1.08` por `1.05`.
- “Reconoce Oeste como región”: no necesitas agregarla; los nombres nuevos se
  conservan. Sólo modifica `REGION_CANONICA` si quieres homologar otra escritura.
- “La promoción ahora tiene tres valores”: abre `limpieza_datos.py`, cambia la
  validación y luego adapta el efecto en `modelo_demanda.py`.
- “Muestra otra gráfica”: abre únicamente `dashboard.py`.
