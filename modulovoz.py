import whisper
import sounddevice as sd
import numpy as np
import queue
import warnings

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

print("Cargando modelo de voz Whisper 'small' (mayor precisión)...")
# 1. CAMBIO: De "base" a "small"
modelo_whisper = whisper.load_model("small")

cola_audio = queue.Queue()
grabando = False
stream = None

def callback_audio(indata, frames, time, status):
    if grabando:
        cola_audio.put(indata.copy())

def iniciar_grabacion():
    global grabando, stream, cola_audio
    cola_audio = queue.Queue()
    grabando = True
    
    stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', callback=callback_audio)
    stream.start()
    print("Micrófono abierto, grabando...")

def detener_y_transcribir():
    global grabando, stream
    grabando = False
    if stream is not None:
        stream.stop()
        stream.close()
    
    print("Micrófono cerrado. Uniendo audio...")
    
    datos = []
    while not cola_audio.empty():
        datos.append(cola_audio.get())
        
    if not datos:
        return ""
        
    audio_completo = np.concatenate(datos, axis=0)
    audio_aplanado = audio_completo.flatten()
    
    print("Traduciendo voz a texto...")
    
    # 2. CAMBIO: Contexto para forzar el vocabulario correcto
    contexto_previo = "Hola, me llamo Héctor. Este proyecto es un traductor de otomí o ñañho."
    
    # 3. CAMBIO: Nuevos parámetros de precisión
    resultado = modelo_whisper.transcribe(
        audio_aplanado, 
        language="es",
        initial_prompt=contexto_previo,
        condition_on_previous_text=False # Apaga la alucinación en inglés
    )
    
    return resultado["text"].strip()