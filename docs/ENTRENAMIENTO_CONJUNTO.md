# Entrenamiento del traductor español → otomí

El corpus combinado tiene 341 pares para entrenamiento, 36 para validación y 38 para prueba. El script comprueba los IDs, la codificación, la coincidencia CSV/JSONL y que ningún texto español ni relato fuente cruce particiones. Mantiene etiquetas distintas para Santiago Mexquititlán y San Ildefonso Tultepec. La confirmación de hablantes fue comunicada de forma global por el usuario, sin hojas de revisión por fila adjuntas.

## Preparar Windows

Desde la raíz del proyecto, con Python 3.11 o posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

En esta computadora quedó instalada la versión CUDA 12.8 de PyTorch 2.11.0, obtenida del índice oficial de [PyTorch](https://pytorch.org/get-started/locally/). Para repetir esta instalación en un entorno nuevo:

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.11.0+cu128 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

La laptop detectada tiene una RTX 4050 con 6 GB. El script usa lotes de uno, acumulación de gradientes, checkpointing y Adafactor para reducir memoria. En esta GPU se completaron entrenamientos de ByT5-small con LoRA y con ajuste completo. Para el ajuste completo se cargan los pesos en BF16 cuando la GPU lo admite; cargarlos en FP32 produjo errores de memoria. `--allow-cpu` permite un ensayo muy lento.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --baseline
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --train
```

El primer comando verifica los datos sin descargar modelos. El segundo evalúa una línea base de similitud de caracteres con `scikit-learn` **solo sobre validación** y usando únicamente ejemplos de entrenamiento. El tercero ajusta LoRA, selecciona el mejor checkpoint por pérdida de validación, detiene el proceso si deja de mejorar y evalúa prueba una vez. Los resultados quedan en `runs/byt5_lora/`: adaptador, predicciones y `metricas.json` con coincidencia exacta, CER y chrF por variedad y tipo. Para un modelo distinto, usa `--model-name`, `--input-format natural` si su tokenizador no admite las etiquetas entre corchetes, y otro `--output-dir`. No ajustes hiperparámetros mirando los resultados de prueba.

## Resultados medidos el 5 de noviembre de 2026

| Método | Validación: exactos | Validación: chrF | Validación: CER | Prueba: exactos | Prueba: chrF |
|---|---:|---:|---:|---:|---:|
| Vecino más cercano, ajustado solo con entrenamiento | 0/36 | 11.24 | 0.9430 | no evaluado | no evaluado |
| ByT5-small, LoRA | 0/36 | 1.22 | 7.0883 | 0/38 | 1.20 |
| ByT5-small, ajuste completo BF16 | 0/36 | 7.79 | 2.1567 | 0/38 | 4.91 |
| IndT5, ajuste completo BF16 | 0/36 | 2.65 | 1.8148 | 0/38 | 2.58 |

Estas métricas no justifican traducir texto nuevo automáticamente. ByT5 repite fragmentos o copia español; IndT5 genera a menudo la misma palabra para entradas distintas y repite sílabas. Son experimentos de referencia. Hay solo 341 pares de entrenamiento y ninguna oración paralela de Santiago; la confirmación comunicada por hablantes no mide la generalización. Los resultados por variedad y tipo están en `reports/*_metricas.json`; las predicciones y los pesos quedan en `Desktop/OTOMI/runs/`. La prueba se consultó para informar los resultados, no para elegir hiperparámetros; cualquier selección posterior basada en ella sería exploratoria.

IndT5 se eligió porque su [modelo publicado](https://huggingface.co/UBC-NLP/IndT5) fue preentrenado también con español y hñähñu. Esa procedencia no garantiza compatibilidad con las dos variedades del corpus. Se usó entrada en lenguaje natural porque su tokenizador no representa las etiquetas `<variante><tipo>`. El mejor checkpoint por pérdida de validación fue el de la época 11; la parada temprana terminó el ajuste en la 14. Para reproducirlo:

```powershell
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --train --full-finetune --model-name UBC-NLP/IndT5 --input-format natural --output-dir runs/indt5_full
```

El modo de consulta exacta usa las 415 filas confirmadas del CSV, incluidas las particiones reservadas para evaluar generalización. Por eso su cobertura de entradas conocidas **no debe informarse como una puntuación de prueba independiente**. Para medir un algoritmo de recuperación se usaron solo las 341 filas de entrenamiento. La siguiente mejora real requiere nuevos pares revisados por hablantes, especialmente oraciones de Santiago y ejemplos nuevos de ambas variedades para una prueba posterior.

El adaptador **no contiene los pesos completos de ByT5**. Para usarlo, `scripts/inferencia_otomi.py` carga el modelo base y luego el adaptador. Por ejemplo:

```powershell
.\.venv\Scripts\python.exe scripts\inferencia_otomi.py "arena" --variante san_ilde_tultepec
.\.venv\Scripts\python.exe scripts\inferencia_otomi.py "ya tengo hambre." --variante san_ilde_tultepec --tipo oracion
```

La inferencia devuelve de inmediato una traducción exacta confirmada si el texto está en el CSV. Para texto desconocido se abstiene. `--experimental-model` activa explícitamente la generación neuronal con ByT5 completo de forma predeterminada y etiqueta la respuesta como experimental. Para inspeccionar IndT5, añade `--model-dir runs/indt5_full/modelo_final`. No inventa una puntuación de confianza. Santiago tiene 214 entradas léxicas y **ninguna oración paralela**, por lo que la inferencia se abstiene ante oraciones nuevas de esa variedad incluso en modo experimental.

El `entrenamiento.py` anterior usa NLLB y el JSONL antiguo. El mockup de Flet y la síntesis/reconocimiento de voz quedan para la segunda fase. Los seis audios de referencia todavía necesitan transcripción, variante y alineación con texto confirmadas por hablantes antes de entrenar o evaluar una voz otomí. Las librerías de audio, TensorFlow y Keras no mejoran por sí mismas el ajuste de este corpus textual y no se cargan en el entrenamiento.
