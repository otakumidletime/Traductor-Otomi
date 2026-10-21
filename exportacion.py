import sqlite3
import json

def exportar_para_entrenamiento(ruta_salida):
    con = sqlite3.connect('otomitraductor.db')
    cursor = con.cursor()

    cursor.execute("SELECT espanol, otomi FROM texto WHERE validacion = 'aprobado'")
    filas = cursor.fetchall()

    with open(ruta_salida, 'w', encoding='utf-8') as archivo_json:
        for fila in filas:
            espanol, otomi = fila
            registro = {"traductor": {"es": espanol, "oto": otomi}}
            archivo_json.write(json.dumps(registro, ensure_ascii=False) + '\n')

    con.close()
    print(f"Exportacion exitosa: {len(filas)} oraciones validadas en {ruta_salida}")

if __name__ == "__main__":
    exportar_para_entrenamiento('dataset_entrenamiento.jsonl')