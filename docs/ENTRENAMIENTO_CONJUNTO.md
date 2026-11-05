# Entrenamiento del traductor español → otomí

El corpus combinado tiene 341 pares para entrenamiento, 36 para validación y 38 para prueba. El script comprueba los IDs, la codificación, la coincidencia CSV/JSONL y que ningún texto español ni relato fuente cruce particiones. Mantiene etiquetas distintas para Santiago Mexquititlán y San Ildefonso Tultepec. La confirmación de hablantes fue comunicada de forma global por el usuario, sin hojas de revisión por fila adjuntas.

## Preparar Windows

Desde la raíz del proyecto, con Python 3.11 o posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Instala **PyTorch con CUDA** usando el selector oficial de [PyTorch](https://pytorch.org/get-started/locally/), eligiendo Windows, Pip y la versión CUDA compatible. Hazlo dentro del entorno virtual. Después:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

La laptop detectada tiene una RTX 4050 con 6 GB. El script usa ByT5-small con un adaptador LoRA, lotes de uno, acumulación de gradientes, checkpointing y Adafactor para reducir memoria. Esa configuración **puede** caber, pero no se ha ejecutado aquí: faltan los paquetes neuronales. Si se agota la memoria, cierra otras aplicaciones que usen la GPU o usa una GPU mayor. `--allow-cpu` permite un ensayo muy lento.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --baseline
.\.venv\Scripts\python.exe scripts\entrenar_otomi.py --train
```

El primer comando verifica los datos sin descargar modelos. El segundo evalúa una línea base de similitud de caracteres con `scikit-learn` **solo sobre validación** y usando únicamente ejemplos de entrenamiento. El tercero ajusta LoRA, selecciona el mejor checkpoint por pérdida de validación, detiene el proceso si deja de mejorar y evalúa prueba una vez. Los resultados quedan en `runs/byt5_lora/`: adaptador, predicciones y `metricas.json` con coincidencia exacta, CER y chrF por variedad y tipo. No ajustes hiperparámetros mirando los resultados de prueba.

El adaptador **no contiene los pesos completos de ByT5**. Para usarlo, `scripts/inferencia_otomi.py` carga el modelo base y luego el adaptador. Por ejemplo:

```powershell
.\.venv\Scripts\python.exe scripts\inferencia_otomi.py "arena" --variante san_ilde_tultepec
.\.venv\Scripts\python.exe scripts\inferencia_otomi.py "ya tengo hambre." --variante san_ilde_tultepec --tipo oracion
```

La inferencia devuelve de inmediato una traducción exacta confirmada si el texto está en el CSV. Para texto desconocido usa el modelo entrenado; si aún no existe el adaptador, indica que falta. No inventa una puntuación de confianza. Santiago tiene 214 entradas léxicas y **ninguna oración paralela**, por lo que la inferencia se abstiene ante oraciones nuevas de esa variedad.

El `entrenamiento.py` anterior usa NLLB y el JSONL antiguo. El mockup de Flet y la síntesis/reconocimiento de voz quedan para la segunda fase. Los seis audios de referencia todavía necesitan transcripción, variante y alineación con texto confirmadas por hablantes antes de entrenar o evaluar una voz otomí. Las librerías de audio, TensorFlow y Keras no mejoran por sí mismas el ajuste de este corpus textual y no se cargan en el entrenamiento.
