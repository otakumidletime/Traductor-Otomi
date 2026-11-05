# Dataset conjunto definitivo español → otomí

[`data/dataset_conjunto_definitivo_es_otomi.csv`](../data/dataset_conjunto_definitivo_es_otomi.csv) reúne los **415 pares aptos** seleccionados de los dos libros: **214 entradas léxicas de Santiago Mexquititlán**, **47 léxicas de San Ildefonso Tultepec** y **154 oraciones de San Ildefonso Tultepec**. No incorpora la norma hñähñu, la antigua fila de prueba `pruebaespanol`, topónimos etimológicos ni hallazgos crudos con codificación dudosa. De los 906 registros de revisión, 483 quedaron excluidos por criterios documentados y ocho testimonios repetidos se fusionaron.

El usuario comunicó el **5 de noviembre de 2026** que hablantes de **ambas** variedades confirmaron los pares seleccionados. La confirmación se registró como **global y comunicada por el usuario**; no se adjuntaron hojas con marcas fila por fila. Para Santiago se había especificado que sus 214 entradas no tuvieron cambios. Para San Ildefonso no se comunicaron correcciones concretas. Estos alcances constan en `validacion_hablante` y `alcance_validacion`.

## Particiones para el modelo conjunto

| Variedad | Tipo | Entrenamiento | Validación | Prueba | Total |
|---|---|---:|---:|---:|---:|
| Santiago Mexquititlán | Léxico | 172 | 21 | 21 | 214 |
| San Ildefonso Tultepec | Léxico | 36 | 6 | 5 | 47 |
| San Ildefonso Tultepec | Oración | 133 | 9 | 12 | 154 |
| **Total** | | **341** | **36** | **38** | **415** |

Una entrada del léxico de San Ildefonso cambió de partición al unir los conjuntos, para que la misma expresión española no quedara a la vez en entrenamiento y validación. Se agruparon también los ejemplos de cada texto narrativo citado del Vol. I. Se verificó que ningún texto español normalizado ni texto narrativo citado cruce particiones.

## Columnas y uso

`espanol` y `otomi` conservan los pares; `variante_id` distingue `santiago_mexquititlan` de `san_ilde_tultepec`; `tipo_unidad` distingue `lexico` de `oracion`. `fuente`, `pagina_pdf`, `referencia` e `id` permiten revisar el original. La fuente de Amealco agrupa comunidades sin atribuir cada entrada, por lo que `procedencia_variante_fuente` conserva esa limitación aunque el hablante de Santiago haya confirmado el uso.

Para un solo modelo condicionado, `entrada_modelo` ya incluye las etiquetas de variedad y tipo. Por ejemplo, `<santiago_mexquititlan><lexico> Agua` tiene como `salida_modelo` `Dehe`; `<san_ilde_tultepec><oracion> ya tengo hambre.` tiene como salida `ya dí tunthü`. Estas etiquetas impiden que dos formas de distintas variedades se presenten como una sola traducción indistinta.

Los archivos `data/dataset_conjunto_entrenamiento.jsonl`, `data/dataset_conjunto_validacion.jsonl` y `data/dataset_conjunto_test.jsonl` contienen exactamente las mismas filas repartidas por `split`. El script `scripts/entrenar_byt5_conjunto.py` comprueba los datos por defecto al ejecutar `python scripts/entrenar_byt5_conjunto.py` desde la raíz del repositorio. Con `--train` ofrece un ensayo con [ByT5-small](https://huggingface.co/google/byt5-small), que procesa UTF-8 sin exigir un código de idioma otomí; requiere `torch`, `datasets`, `transformers`, `accelerate`, descargar los pesos y preferentemente una GPU CUDA. **No se ejecutó el ajuste fino** en este equipo porque esas dependencias no están instaladas. La comprobación de archivos y la sintaxis del script sí pasaron.

## Alcance lingüístico

Este es el conjunto completo **de pares filtrados y confirmados que tenemos de estos dos libros**. Aumenta las muestras para entrenar un prototipo, pero la composición sigue desigual: Santiago aporta léxico y ninguna oración paralela; San Ildefonso aporta todas las 154 oraciones. Un buen resultado global no demostraría por sí solo traducción de oraciones a Santiago. Conviene evaluar cada combinación de `variante_id` y `tipo_unidad` por separado y ampliar las oraciones de Santiago antes de usar el sistema fuera de pruebas.

Control final: 415 IDs y pares únicos; cero filas vacías, caracteres de sustitución, registros de la norma o filas de prueba antiguas; Unicode NFC; etiquetas y salidas coherentes; sin cruces entre particiones. Los 214 pares de Santiago se localizaron en sus páginas PDF y los 201 de San Ildefonso en 137 páginas descifradas del Vol. I. El CSV usa UTF-8 con BOM.
