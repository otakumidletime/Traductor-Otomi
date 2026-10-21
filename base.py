import sqlite3

def create_database():
    con = sqlite3.connect('otomitraductor.db')
    cursor = con.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fuentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        puntuacion INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS texto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        espanol TEXT NOT NULL,
        otomi TEXT NOT NULL,
        fuentesid INTEGER,
        validacion TEXT DEFAULT 'pendiente',
        notas TEXT,
        FOREIGN KEY (fuentesid) REFERENCES fuentes (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        textoid INTEGER NOT NULL,
        ruta TEXT NOT NULL,
        duracion REAL,
        FOREIGN KEY (textoid) REFERENCES texto (id)
    )
    ''')

    con.commit()
    con.close()
    print("Base de Datos creada con exito")

if __name__ == "__main__":
    create_database()
