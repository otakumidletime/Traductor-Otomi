from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

print("Cargando modelo de Inteligencia Artificial. Por favor espera...")

# Cargar el modelo entrenado desde la carpeta local
RUTA_MODELO = "./modelo_otomi_final"
tokenizer = AutoTokenizer.from_pretrained(RUTA_MODELO)
modelo = AutoModelForSeq2SeqLM.from_pretrained(RUTA_MODELO)

def traducir_es_a_oto(texto_espanol):
    """Recibe un string en español y devuelve la traducción en otomí."""
    if not texto_espanol.strip():
        return ""
        
    # Convertir el texto a números (tokens) que la IA entiende
    inputs = tokenizer(texto_espanol, return_tensors="pt", max_length=128, truncation=True)
    
    # Generar la traducción matemática con reglas estrictas anti-inglés
    outputs = modelo.generate(
        **inputs, 
        max_length=128,
        num_beams=5,               # Aumenta la precisión de búsqueda
        repetition_penalty=2.5,    # Castiga la repetición
        temperature=0.3,           # <-- Hace a la IA más robótica y menos creativa (evita el inglés)
        do_sample=True,
        early_stopping=True
    )
    
    # Decodificar el resultado matemático de vuelta a texto legible
    traduccion = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    return traduccion