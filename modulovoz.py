import os
os.add_dll_directory(r"E:\basedatos")
import whisper
import sounddevice as sd
import numpy as np
import queue
import warnings
import sounddevice as sd
import soundfile as sf
from TTS.api import TTS

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

print("Cargando modelo de voz Ñañho en memoria...")
modelo_tts = TTS(
    model_path="./modelo_voz_otomi",
    config_path="./modelo_voz_otomi/config.json"
).to("cpu")

# NUEVA VARIABLE: Actúa como la memoria del último texto procesado
ultimo_texto_generado = ""

def generar_y_reproducir_audio(texto_otomi):
    global ultimo_texto_generado
    ruta_salida = "audio_generado_temporal.wav"
    
    # Condición: Si el texto es nuevo, o el archivo de audio no existe, generamos uno nuevo.
    if texto_otomi != ultimo_texto_generado or not os.path.exists(ruta_salida):
        print(f"Texto nuevo detectado. Generando voz de XTTS...")
        modelo_tts.tts_to_file(
            text=texto_otomi,
            speaker_wav="./modelo_voz_otomi/reference.wav",
            language="es",
            file_path=ruta_salida
        )
        # Actualizamos la memoria para la próxima vez que el usuario haga clic
        ultimo_texto_generado = texto_otomi
    else:
        print("Texto idéntico al anterior. Reproduciendo desde caché...")
    
    # Reproducimos el audio final (ya sea el recién creado o el almacenado)
    data, fs = sf.read(ruta_salida)
    sd.play(data, fs)
    sd.wait()
