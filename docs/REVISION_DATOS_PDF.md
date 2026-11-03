# Extracción inicial para el traductor español–otomí

## Qué se extrajo

- **374 candidatos** de los apéndices de *Ar ñäñho hongar nzaki. El otomí en busca de la vida*, de Lydia van de Fliert, con un estudio histórico de David Charles Wright Carr. El PDF tiene 402 páginas; las filas se tomaron de las páginas PDF 359–374. El nombre local del archivo menciona un «glosario de Tolimán», pero la portada identifica la obra y las comunidades de Santiago Mexquititlán y San Ildefonso Tultepec, Amealco, Querétaro.
- **341 candidatos adicionales** del glosario de la *Norma de escritura de la lengua Hñähñu (otomí)* de INALI (225 páginas PDF), en páginas PDF 206–209: 313 formas presentadas como sinónimos entre variantes y 28 formas de la sección «Palabras nuevas». El glosario reúne variantes sin asignar cada forma a una región concreta; no se debe atribuir automáticamente su vocabulario a Amealco.

El CSV combinado reúne **715 filas** y mantiene la procedencia de cada una. Los dos CSV por fuente facilitan la revisión separada.

| Categoría del libro de UAQ | Candidatos |
|---|---:|
| Plantas y herbolaria | 124 |
| Vocabulario general | 85 |
| Parentesco y estado civil | 56 |
| Fauna y medicina tradicional | 36 |
| Líquidos, alimentos y minerales | 29 |
| Cuerpo humano | 22 |
| Milpa y maíz | 18 |
| Direcciones | 4 |

El CSV usa UTF-8 con BOM para facilitar su apertura en Excel. Cada fila tiene `espanol`, `otomi`, `variante`, `categoria`, `contexto`, `nombre_cientifico`, `calidad_tradicional`, `fuente`, `pagina_pdf`, `estado_revision` y `notas`. **Todas las filas están en `pendiente`: son propuestas de transcripción, no datos aprobados para entrenar.** En ambos PDF hay subrayados vocálicos visibles que la capa de texto puede perder; el cotejo visual de muestras y de la alineación de tablas no equivale a revisar la grafía de las 715 filas una por una. La clasificación tradicional «caliente/frío» de los cuadros de medicina se conserva como metadato, no como significado de la palabra.

## Hallazgos de la norma

La página PDF 153 (impresa 151) presenta 22 consonantes, dos semiconsonantes y 14 vocales en la propuesta de escritura. La página PDF 173 (impresa 171) distingue tonos mediante vocales dobles, tilde y ausencia de marca. Las páginas PDF 185–189 tratan composición y derivación; 198–203, préstamos y neologismos. Algunas vocales llevan un subrayado significativo. La extracción de texto de este PDF pierde el subrayado y sustituye varios caracteres por `�`. Por ello se revisó visualmente la alineación del glosario, pero los candidatos siguen marcados como pendientes hasta que un hablante o especialista confirme su grafía y variante. Se debe conservar la ortografía original y definir con la comunidad cómo codificar los subrayados en Unicode antes de normalizar o entrenar.

## Comparación con el repositorio

El `dataset_entrenamiento.jsonl` público contiene 239 pares y uno es de prueba (`pruebaespanol` → `pruebaotomi`). El nuevo CSV comparte siete entradas españolas con el archivo actual: tres coinciden exactamente y cuatro muestran otra forma: **cebada, ardilla, sal y fuerte**. Estas cuatro filas llevan una nota de revisión. Las diferencias pueden responder a variante, grafía o sentido; no se sustituyeron las entradas existentes.

El importador actual (`insercion.py`) lee las dos columnas básicas del CSV, pero descarta variante, página y notas. La tabla de `base.py` aún no tiene campos propios para esos metadatos. `exportacion.py` sobrescribe el JSONL de entrenamiento con los registros aprobados de SQLite. Conviene ampliar el esquema y conservar ambos tipos de datos antes de usar la importación.

El entrenamiento actual (`entrenamiento.py`) no separa un conjunto de evaluación y usa NLLB sin configurar explícitamente los idiomas. La [documentación de NLLB](https://huggingface.co/docs/transformers/main/model_doc/nllb) indica que la lengua de origen y el token de destino deben configurarse. La [lista de tokens del modelo](https://huggingface.co/facebook/nllb-200-distilled-600M/raw/main/special_tokens_map.json) incluye español y no presenta un token de otomí. Por tanto, entrenar 40 épocas sobre unas centenas de vocablos no demuestra que el sistema traduzca oraciones al ñäñho. La [ficha del modelo](https://huggingface.co/facebook/nllb-200-distilled-600M) también describe un uso de investigación y licencia CC BY-NC 4.0.

## Cómo revisar e integrar

1. Filtrar los CSV por `estado_revision=pendiente`. Revisar cada fila en la página indicada, sobre todo subrayados, diacríticos, apóstrofos, alternativas separadas por coma o barra y frases con varios sentidos. El CSV combinado no debe usarse como conjunto homogéneo de entrenamiento porque junta fuentes y variantes diferentes.
2. Registrar quién validó la forma, su comunidad y la variante. Separar alternativas en filas distintas solo cuando un hablante confirme que son equivalentes en el contexto anotado.
3. Confirmar las condiciones de reutilización del libro de UAQ antes de publicar el CSV en GitHub. El permiso para el diccionario de Dani Pérez no cubre automáticamente estos otros PDF.
4. Mantener glosario y oraciones paralelas en conjuntos separados. Probar primero una búsqueda por glosario validado; para traducción de frases, reunir pares de oraciones revisados y reservar parte de ellos para evaluación.

Para repetir la extracción del libro de UAQ:

```powershell
python -m pip install pdfplumber
python scripts/extraer_toliman.py --pdf "RUTA_AL_LIBRO.pdf" --out "data/candidatos_espanol_nanho.csv" --existing-jsonl "dataset_entrenamiento.jsonl"
python scripts/extraer_glosario_norma.py --pdf "RUTA_A_LA_NORMA.pdf" --out "data/candidatos_norma_hnahnu.csv"
python scripts/combinar_candidatos.py data/candidatos_espanol_nanho.csv data/candidatos_norma_hnahnu.csv --out data/candidatos_espanol_otomi_combinado.csv
```

La selección de páginas y el diseño de tablas del script corresponden a esta edición específica del libro.
