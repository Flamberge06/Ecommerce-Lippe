import json
import psycopg2
import sqlite3

# 1. Verbindung zu SQLite
sqlite_conn = sqlite3.connect("Ecommerce Lippe.db")
sqlite_conn.row_factory = sqlite3.Row  # Zugriff über Spaltennamen ermöglichen
sqlite_cursor = sqlite_conn.cursor()

# 2. Verbindung zu PostgreSQL
pg_conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="dbbpostger_123",
    host="localhost",
    port="5432"
)
pg_conn.autocommit = True
pg_cursor = pg_conn.cursor()

# Tabelle in PostgreSQL anlegen
pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS artikel_gesamt (
        id TEXT PRIMARY KEY,
        kategorie TEXT,
        preis NUMERIC,
        eigenschaften JSONB
    )
""")

# 3. Daten aus SQLite holen
sqlite_cursor.execute("SELECT * FROM artikel_gesamt")
rows = sqlite_cursor.fetchall()

standard_spalten = ["id", "kategorie", "preis"]
übertragene_anzahl = 0

# 4. Zeile für Zeile konvertieren
for row in rows:
    row_dict = dict(row)

    p_id = row_dict.get("id")
    kategorie = row_dict.get("kategorie")
    preis = row_dict.get("preis")

    # Alle Spalten, die nicht NULL sind und nicht zu den Standard-Spalten gehören, ins JSON packen
    eigenschaften = {
        k: v for k, v in row_dict.items()
        if k not in standard_spalten and v is not None and v != ""
    }

    # In PostgreSQL einfügen
    pg_cursor.execute("""
        INSERT INTO produkte (id, kategorie, preis, eigenschaften)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE 
        SET kategorie = EXCLUDED.kategorie,
            preis = EXCLUDED.preis,
            eigenschaften = EXCLUDED.eigenschaften;
    """, (p_id, kategorie, preis, json.dumps(eigenschaften)))

    übertragene_anzahl += 1

print(f"Fertig! {übertragene_anzahl} Produkte erfolgreich nach PostgreSQL migriert.")

sqlite_conn.close()
pg_conn.close()