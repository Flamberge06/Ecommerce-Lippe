import json
from db import get_connection  # Zentrale DB-Verbindung importieren

# 1. Verbindung aufbauen
conn = get_connection()
conn.autocommit = True
cursor = conn.cursor()

# 2. Tabelle erstellen (falls noch nicht vorhanden)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS produkte (
        id TEXT PRIMARY KEY,
        kategorie TEXT,
        preis NUMERIC,
        eigenschaften JSONB
    )
""")

# 3. Funktion zum Einfügen von Produkten
def erstelle_produkt(p_id, kategorie, preis, eigenschaften):
    query = """
        INSERT INTO produkte (id, kategorie, preis, eigenschaften)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """
    cursor.execute(query, (p_id, kategorie, preis, json.dumps(eigenschaften)))
    print(f"Produkt {p_id} erfolgreich verarbeitet.")

# 4. Beispiel-Aufruf ausführen
erstelle_produkt(
    "B011",
    "Bücher",
    19.99,
    {"titel": "Clean Code", "isbn": "978-0132350884"}
)

cursor.close()
conn.close()