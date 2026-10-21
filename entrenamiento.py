from datasets import load_dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Seq2SeqTrainingArguments, Seq2SeqTrainer

# 1. Cargar el dataset exportado
dataset = load_dataset('json', data_files='dataset_entrenamiento.jsonl')

# 2. Cargar el modelo base (NLLB-200 de 600M es la versión más ligera para pruebas)
modelo_base = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(modelo_base)
model = AutoModelForSeq2SeqLM.from_pretrained(modelo_base)

# 3. Función para convertir el texto en números (Tokens) que la IA entiende
def preparar_datos(ejemplos):
    # Extraemos el español y el otomí del formato JSON
    inputs = [ex["es"] for ex in ejemplos["traductor"]]
    targets = [ex["oto"] for ex in ejemplos["traductor"]]
    
    model_inputs = tokenizer(inputs, max_length=128, truncation=True)
    labels = tokenizer(text_target=targets, max_length=128, truncation=True)
    
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# Aplicar la tokenización a todo el archivo
dataset_tokenizado = dataset.map(preparar_datos, batched=True)

# 4. Configurar los parámetros de entrenamiento (hiperparámetros)
args = Seq2SeqTrainingArguments(
    output_dir="./modelo_otomi_checkpoints",
    learning_rate=2e-5,
    per_device_train_batch_size=4,  # Reducir a 2 si tu computadora se queda sin memoria
    weight_decay=0.01,
    save_total_limit=2,
    num_train_epochs=3,             # Número de veces que la IA leerá todo el dataset
    predict_with_generate=True,
    logging_steps=10
)

# 5. Iniciar el motor de entrenamiento
trainer = Seq2SeqTrainer(
    model=model,
    args=args,
    train_dataset=dataset_tokenizado["train"],
    tokenizer=tokenizer,
)

print("Iniciando entrenamiento...")
trainer.train()

# 6. Guardar el modelo final en tu computadora
trainer.save_model("./modelo_otomi_final")
print("Modelo guardado exitosamente en la carpeta '/modelo_otomi_final'")