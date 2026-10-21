import sqlite3
import csv

def cargar_csv_a_db(ruta, idfuentes):
    con = sqlite3.connect('otomitraductor.db')
    cursor = con.cursor()

    with open(ruta, 'r', encoding='utf-8-sig') as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            cursor.execute('''
                INSERT INTO texto (espanol, otomi, fuentesid, validacion)
                VALUES (?, ?, ?, 'pendiente')
            ''', (fila['espanol'], fila['otomi'], idfuentes))

    con.commit()
    con.close()
    print("Datos cargador con exito")

if __name__ == "__main__":
    cargar_csv_a_db('datoscrudo.csv', 1)
