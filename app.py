import customtkinter as ctk
# Importamos la función de nuestro archivo puente
from traductoria import traducir_es_a_oto

def ejecutar_traduccion():
    # 1. Obtener lo que el usuario escribió
    texto_entrada = caja_espanol.get("1.0", "end-1c")
    
    # 2. Enviar a la IA (Esto puede tardar un par de segundos)
    resultado_otomi = traducir_es_a_oto(texto_entrada)
    
    # 3. Mostrar el resultado borrando lo que había antes
    caja_otomi.delete("1.0", "end")
    caja_otomi.insert("1.0", resultado_otomi)

# --- CONFIGURACIÓN DE LA INTERFAZ ---
ctk.set_appearance_mode("dark")
ventana = ctk.CTk()
ventana.geometry("500x450")
ventana.title("Traductor Español - Ñañho")

# Elementos de Español
etiqueta_es = ctk.CTkLabel(ventana, text="Español:", font=("Arial", 16, "bold"))
etiqueta_es.pack(pady=(20, 5))

caja_espanol = ctk.CTkTextbox(ventana, height=100, font=("Arial", 14))
caja_espanol.pack(padx=20, fill="x")

# Botón de acción
boton = ctk.CTkButton(ventana, text="Traducir al Ñañho", command=ejecutar_traduccion, fg_color="#2b7b5c")
boton.pack(pady=20)

# Elementos de Otomí
etiqueta_oto = ctk.CTkLabel(ventana, text="Ñañho (Amealco):", font=("Arial", 16, "bold"))
etiqueta_oto.pack(pady=5)

caja_otomi = ctk.CTkTextbox(ventana, height=100, font=("Arial", 14))
caja_otomi.pack(padx=20, fill="x")

# Iniciar la aplicación
ventana.mainloop()
