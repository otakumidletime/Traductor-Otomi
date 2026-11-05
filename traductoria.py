from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

print("Cargando modelo de Inteligencia Artificial. Por favor espera...")

RUTA_MODELO = "./modelo_otomi_final"
# Le decimos al sistema que la salida esperada es nuestro "disfraz"
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", use_fast=False, src_lang="spa_Latn", tgt_lang="quy_Latn")
modelo = AutoModelForSeq2SeqLM.from_pretrained(RUTA_MODELO)

def traducir_es_a_oto(texto_espanol):
    """Recibe un string en español y devuelve la traducción en otomí."""
    if not texto_espanol.strip():
        return ""

    inputs = tokenizer(texto_espanol, return_tensors="pt", max_length=128, truncation=True)
    
    # Bloqueamos el idioma usando la nueva etiqueta
    forced_token_id = tokenizer.lang_code_to_id["quy_Latn"]

    outputs = modelo.generate(
        **inputs,
        forced_bos_token_id=forced_token_id,
        max_length=128,
        num_beams=5,
        early_stopping=True
    )

    traduccion = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return traduccion
