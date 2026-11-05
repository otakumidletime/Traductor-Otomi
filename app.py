import os
os.add_dll_directory(r"E:\basedatos")
import customtkinter as ctk
import threading
from traductoria import traducir_es_a_oto
from modulovoz import iniciar_grabacion, detener_y_transcribir, generar_y_reproducir_audio

estado_grabando = False

def ejecutar_traduccion_texto():
    texto_entrada = caja_espanol.get("1.0", "end-1c")
    if texto_entrada.strip():
        resultado_otomi = traducir_es_a_oto(texto_entrada)
        caja_otomi.delete("1.0", "end")
        caja_otomi.insert("1.0", resultado_otomi)

def manejar_boton_voz():
    global estado_grabando
    
    if not estado_grabando:
        # FASE 1: INICIAR GRABACIÓN
        estado_grabando = True
        boton_voz.configure(text="🛑 Detener y Traducir", fg_color="#c0392b")
        iniciar_grabacion()
    else:
        # FASE 2: DETENER Y PROCESAR
        estado_grabando = False
        boton_voz.configure(text="⚙️ Procesando audio...", fg_color="#d35400", state="disabled")
        threading.Thread(target=procesar_audio_en_fondo).start()

def procesar_audio_en_fondo():
    texto_escuchado = detener_y_transcribir()
    ventana.after(0, actualizar_interfaz, texto_escuchado)

def actualizar_interfaz(texto_escuchado):
    if texto_escuchado:
        caja_espanol.delete("1.0", "end")
        caja_espanol.insert("1.0", texto_escuchado)
        
        resultado_otomi = traducir_es_a_oto(texto_escuchado)
        caja_otomi.delete("1.0", "end")
        caja_otomi.insert("1.0", resultado_otomi)
    
    boton_voz.configure(text="🎙️ Hablar por Micrófono", fg_color="#2980b9", state="normal")

def ejecutar_reproduccion_voz():
    texto_otomi = caja_otomi.get("1.0", "end-1c")
    if texto_otomi.strip():
        boton_reproducir.configure(text="⏳ Generando voz...", fg_color="#d35400", state="disabled")
        threading.Thread(target=hilo_reproduccion, args=(texto_otomi,)).start()

def hilo_reproduccion(texto):
    generar_y_reproducir_audio(texto)
    ventana.after(0, lambda: boton_reproducir.configure(text="🔊 Escuchar Traducción", fg_color="#8e44ad", state="normal"))

# --- CONFIGURACIÓN DE LA INTERFAZ ---
ctk.set_appearance_mode("dark")
ventana = ctk.CTk()
ventana.geometry("500x600")
ventana.title("Traductor Español - Ñañho")

# Elementos de Español
etiqueta_es = ctk.CTkLabel(ventana, text="Español:", font=("Arial", 16, "bold"))
etiqueta_es.pack(pady=(20, 5))

caja_espanol = ctk.CTkTextbox(ventana, height=100, font=("Arial", 14))
caja_espanol.pack(padx=20, fill="x")

# Marco para alinear los botones (¡Esta es la pieza que faltaba!)
marco_botones = ctk.CTkFrame(ventana, fg_color="transparent")
marco_botones.pack(pady=15)

boton_texto = ctk.CTkButton(marco_botones, text="Traducir Texto", command=ejecutar_traduccion_texto, fg_color="#2b7b5c")
boton_texto.pack(side="left", padx=10)

boton_voz = ctk.CTkButton(marco_botones, text="🎙️ Hablar por Micrófono", command=manejar_boton_voz, fg_color="#2980b9")
boton_voz.pack(side="left", padx=10)

# Elementos de Otomí
etiqueta_oto = ctk.CTkLabel(ventana, text="Ñañho (Amealco):", font=("Arial", 16, "bold"))
etiqueta_oto.pack(pady=5)

caja_otomi = ctk.CTkTextbox(ventana, height=100, font=("Arial", 14))
caja_otomi.pack(padx=20, fill="x")

boton_reproducir = ctk.CTkButton(ventana, text="🔊 Escuchar Traducción", command=ejecutar_reproduccion_voz, fg_color="#8e44ad")
boton_reproducir.pack(pady=15)

ventana.mainloop()
