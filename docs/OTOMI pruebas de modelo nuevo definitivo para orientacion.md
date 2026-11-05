# OTOMI pruebas de modelo nuevo definitivo para orientacion

**Estado al 5 de noviembre de 2026.** Este documento resume las decisiones y pruebas de esta conversación para orientar el siguiente entrenamiento del traductor español → otomí. El nombre del archivo identifica el proyecto; **todavía no existe un modelo neuronal definitivo con calidad suficiente para traducir texto nuevo**.

## Objetivo y fuentes

El objetivo es traducir español a las variedades de Santiago Mexquititlán y San Ildefonso Tultepec, manteniéndolas identificadas por separado. El trabajo partió de la idea de extraer un diccionario en Calaméo y revisar el repositorio `Traductor-Otomi`. Como el PDF original del diccionario no estaba disponible para descarga, el conjunto actual se construyó con *El Glosario Ñäñho de Tolimán* y *Volumen I: Gramática y Textos del Hñöñhö*. La *norma hñähñu* se excluyó por indicación del usuario.

El usuario comunicó que cuenta con autorización para publicar los pares seleccionados de ambos libros y que personas hablantes de Santiago y San Ildefonso confirmaron globalmente los pares. No se adjuntaron hojas de corrección fila por fila; esa limitación se conserva en el CSV.

## Dataset disponible

El [CSV conjunto](../data/dataset_conjunto_definitivo_es_otomi.csv) contiene **415 pares** con español, otomí, variedad, tipo de unidad, fuente, página y partición:

| Variedad y tipo | Entrenamiento | Validación | Prueba | Total |
|---|---:|---:|---:|---:|
| Santiago Mexquititlán, léxico | 172 | 21 | 21 | 214 |
| San Ildefonso Tultepec, léxico | 36 | 6 | 5 | 47 |
| San Ildefonso Tultepec, oraciones | 133 | 9 | 12 | 154 |
| **Total** | **341** | **36** | **38** | **415** |

Las particiones JSONL están en `data/dataset_conjunto_{entrenamiento,validacion,test}.jsonl`. El script verifica IDs, Unicode, coincidencia con el CSV y ausencia de cruces de texto español o relato fuente entre particiones. Santiago no tiene oraciones paralelas; no se puede medir ni prometer traducción de oraciones nuevas en esa variedad.

Los 415 pares sirven como diccionario de consulta. Una coincidencia exacta sobre ese CSV **no es una métrica de generalización**, porque el diccionario también contiene las filas de validación y prueba. Para evaluar recuperación se usaron exclusivamente las 341 filas de entrenamiento.

## Entorno y pruebas de entrenamiento

El entorno está en `C:\Users\leopa\Desktop\OTOMI\.venv`. Se verificó PyTorch 2.11.0 con CUDA 12.8 en la NVIDIA RTX 4050 de 6 GB. El [script de entrenamiento](../scripts/entrenar_otomi.py) usa Transformers, Datasets, PEFT para LoRA, lotes de uno, acumulación de gradientes, gradient checkpointing y Adafactor. El ajuste completo carga pesos BF16 para caber en la GPU; los primeros intentos FP32 agotaron la memoria. También se instalaron `scikit-learn`, `sacrebleu`, `sentencepiece` y `protobuf`.

Se completaron tres ajustes con el mismo dataset y las mismas particiones. El checkpoint se seleccionó por pérdida de validación. Los informes reproducibles están en [`reports/`](../reports/); pesos, checkpoints y predicciones completas permanecen en `C:\Users\leopa\Desktop\OTOMI\runs\` y no se suben a Git por tamaño.

| Método | Exactos en validación | chrF validación | CER validación | Exactos en prueba | chrF prueba |
|---|---:|---:|---:|---:|---:|
| Vecino más cercano, solo entrenamiento | 0/36 | 11.24 | 0.9430 | no evaluado | no evaluado |
| ByT5-small con LoRA | 0/36 | 1.22 | 7.0883 | 0/38 | 1.20 |
| ByT5-small, ajuste completo BF16 | 0/36 | 7.79 | 2.1567 | 0/38 | 4.91 |
| IndT5, ajuste completo BF16 | 0/36 | 2.65 | 1.8148 | 0/38 | 2.58 |

ByT5 copió partes del español o repitió texto. IndT5 produjo a menudo la misma forma para palabras distintas y repitió sílabas en oraciones. Su preentrenamiento incluye español y hñähñu, según la [ficha de IndT5](https://huggingface.co/UBC-NLP/IndT5), pero no garantiza coincidencia con estas dos variedades. Los 341 pares actuales no bastaron para obtener traducción neuronal fiable. La prueba se informó después de entrenar; no debe usarse para seguir eligiendo hiperparámetros.

## Comportamiento disponible hoy

La [inferencia](../scripts/inferencia_otomi.py) responde con el par confirmado si encuentra la misma entrada en el CSV. Ante un texto desconocido se abstiene. La opción `--experimental-model` permite ver una hipótesis neuronal identificada como experimental; no la convierte en traducción validada. Ante oraciones nuevas de Santiago se abstiene incluso en ese modo.

Desde `C:\Users\leopa\Desktop\OTOMI`:

```powershell
.\.venv\Scripts\python.exe scripts\inferencia_otomi.py "arena" --variante san_ilde_tultepec
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --baseline
```

La [guía de entrenamiento](ENTRENAMIENTO_CONJUNTO.md) contiene comandos para repetir los ajustes y explica cada informe.

## Cómo avanzar hacia un modelo nuevo

1. **Ampliar pares paralelos revisados por hablantes.** Priorizar oraciones cotidianas de Santiago, que hoy faltan por completo, y añadir más oraciones y vocabulario contextual de San Ildefonso. Registrar para cada par variedad, fuente, hablante/revisor, fecha y versión de corrección.
2. **Separar datos nuevos antes de entrenar.** Reservar una prueba nueva, con textos y hablantes distintos cuando sea posible. Mantener frases relacionadas y variantes de una misma oración en una sola partición para evitar filtraciones.
3. **Revisar la ortografía y tokenización.** El PDF usa tipografía y marcas tonales que pueden extraerse de forma ambigua. Cotejar visualmente las entradas dudosas con el libro y con hablantes antes de corregirlas; no normalizar tonos o diacríticos por intuición.
4. **Repetir una línea base y un ajuste.** Comparar por variedad y por tipo de unidad, con coincidencia exacta, chrF, CER y revisión humana de una muestra de errores. Seleccionar con validación y consultar la prueba nueva una sola vez al cerrar la versión.
5. **Habilitar generación solo al superar la evaluación.** Conservar la consulta exacta y la abstención mientras el modelo no demuestre calidad para texto no visto. No mezclar variedades ni añadir pares externos sin documentar su procedencia y compatibilidad.

La interfaz Flet, el reconocimiento de audio y una voz otomí quedan como segunda fase. Los seis audios de referencia aún requieren transcripción, identificación de variedad, alineación temporal y revisión de hablantes antes de usarlos para entrenar o evaluar voz.

## Estado en GitHub

La rama `datos/dataset-conjunto-definitivo` contiene el dataset, los scripts, la guía y los informes. El commit de los entrenamientos es `865c87c`. El [PR borrador #2](https://github.com/otakumidletime/Traductor-Otomi/pull/2) apunta a `leo-branch` para revisión del administrador. Los modelos guardados localmente no forman parte del PR.
