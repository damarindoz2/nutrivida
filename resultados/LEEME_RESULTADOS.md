# Resultados generados

## Archivo oficial

`Pronostico_NutriVida_2026_FINAL.xlsx` es el único libro de resultados que debe
presentarse como entrega final. Reúne en un solo lugar:

- histórico utilizado por el modelo;
- pronóstico por SKU;
- desglose por región y por canal-región;
- resumen mensual y por categoría;
- promociones recurrentes inferidas;
- pruebas de pesos y del escenario protegido;
- resultados por SKU, categoría y mes;
- detalle de la validación histórica;
- trazabilidad del pronóstico;
- control de que el desglose regional regrese al total del SKU.

El dashboard lee este archivo cuando abre el caso original. Si se carga otro
Excel desde la interfaz, el proceso se recalcula desde los datos nuevos.

## `respaldos_csv/`

Contiene copias de algunas hojas del libro final. Son útiles para abrir los
resultados sin un lector de Excel, revisar diferencias o compartir una tabla
específica. No son modelos separados ni deben presentarse como once entregas
distintas.

## `versiones_anteriores/`

Conserva `Pronostico_NutriVida_2026_INICIAL.xlsx`, la primera propuesta realizada
antes de separar mejor las promociones y validar el escenario protegido. Se
mantiene como antecedente, no como resultado vigente.

## Qué entregar

Para una entrega compacta bastan:

1. el código y su documentación;
2. `Datos_NutriVida.xlsx`, si está permitido redistribuirlo;
3. `Pronostico_NutriVida_2026_FINAL.xlsx`;
4. las instrucciones para ejecutar `dashboard.py`.

La carpeta `respaldos_csv/` puede incluirse como evidencia adicional, pero el
dashboard y el resultado final no dependen de esas copias.
