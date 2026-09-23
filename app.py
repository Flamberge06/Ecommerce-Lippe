import json
import pandas as pd
import streamlit as st
from db import get_connection  # Zentrale DB-Verbindung importieren

st.title("eCommerce Lippe GmbH – Produkt-Verwaltung (PostgreSQL + JSONB)")

# --- TABELLE ANLEGEN ---
conn = get_connection()
conn.autocommit = True
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS produkte (
        id TEXT PRIMARY KEY,
        kategorie TEXT,
        preis NUMERIC,
        eigenschaften JSONB
    )
""")

# --- HILFSFUNKTION FÜR AUTOMATISCHE ID ---
KATEGORIE_PRAEFIXE = {
    "Bücher": "B",
    "Bekleidung": "TS", # Beispiel: TS für T-Shirts, passend zu deinen Daten
    "Tabletop": "TT",   # Beispiel-Präfix
    "Sammelkarten": "SC",
    "Sammelfiguren": "SF",
    "Spiel": "SP",
    "T-Shirt": "TS"
}

def generiere_naechste_id(kategorie, cursor):
    """Ermittelt automatisch die nächste fortlaufende ID."""
    praefix = KATEGORIE_PRAEFIXE.get(kategorie)
    if not praefix:
        raise ValueError(f"Kein Präfix für Kategorie '{kategorie}' definiert.")

    query = """
        SELECT id FROM produkte 
        WHERE id LIKE %s 
        ORDER BY LENGTH(id) DESC, id DESC 
        LIMIT 1;
    """
    cursor.execute(query, (f"{praefix}%",))
    ergebnis = cursor.fetchone()

    if not ergebnis:
        neue_nummer = 1
    else:
        letzte_id = ergebnis[0]
        # Extrahiere den numerischen Teil (funktioniert auch, wenn es Ausreißer wie "0B001" gibt, 
        # solange wir uns an das neue Format halten)
        # Besserer Ansatz für gemischte Altdaten: Wir suchen die erste Zahl im String
        import re
        match = re.search(r'\d+', letzte_id[len(praefix):])
        if match:
             neue_nummer = int(match.group()) + 1
        else:
             # Fallback, falls die Logik fehlschlägt
             neue_nummer = 1

    # Format: Präfix + 3-stellige Nummer (z.B. B011)
    neue_id = f"{praefix}{neue_nummer:03d}"
    return neue_id


# --- STREAMLIT TABS FOR CRUD ---
tab_read, tab_create, tab_update, tab_delete = st.tabs(["READ (Anzeigen)", "CREATE (Erstellen)", "UPDATE (Bearbeiten)", "DELETE (Löschen)"])

# 1. READ (Anzeigen)
with tab_read:
    st.header("Aktuelle Produkte")
    cursor.execute("SELECT id, kategorie, preis, eigenschaften FROM produkte ORDER BY id")
    rows = cursor.fetchall()
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Kategorie", "Preis (€)", "Eigenschaften (JSON)"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Keine Produkte vorhanden.")

# 2. CREATE (Erstellen)
with tab_create:
    st.header("Neues Produkt anlegen")
    with st.form("create_form"):
        # Das manuelle ID-Feld wurde entfernt!
        kategorie = st.selectbox("Kategorie", ["Bücher", "Bekleidung", "Tabletop", "Sammelkarten", "Sammelfiguren", "Spiel", "T-Shirt"])
        preis = st.number_input("Preis (€)", min_value=0.0, step=0.5)
        json_input = st.text_area("Flexible Attribute (als JSON)", '{"titel": "Neuer Titel", "isbn": "12345"}')
        
        submitted = st.form_submit_button("Produkt speichern")
        if submitted:
            try:
                # 1. JSON validieren
                attr_dict = json.loads(json_input)
                
                # 2. Neue ID generieren
                neue_p_id = generiere_naechste_id(kategorie, cursor)
                
                # 3. In Datenbank einfügen
                cursor.execute(
                    "INSERT INTO produkte (id, kategorie, preis, eigenschaften) VALUES (%s, %s, %s, %s)",
                    (neue_p_id, kategorie, preis, json.dumps(attr_dict))
                )
                st.success(f"Produkt mit der automatisch generierten ID **{neue_p_id}** erfolgreich gespeichert!")
                # st.rerun() # Neu laden der Seite um die Änderungen im "Read" Tab sofort zu sehen
            except ValueError as ve:
                 st.error(f"Fehler bei der ID-Generierung: {ve}")
            except Exception as e:
                st.error(f"Fehler: {e}")

# 3. UPDATE (Bearbeiten)
with tab_update:
    st.header("Produkt-Preis oder Attribute aktualisieren")
    cursor.execute("SELECT id FROM produkte ORDER BY id")
    all_ids = [r[0] for r in cursor.fetchall()]
    
    if all_ids:
        selected_id = st.selectbox("Wähle eine ID zum Bearbeiten", all_ids)
        cursor.execute("SELECT kategorie, preis, eigenschaften FROM produkte WHERE id = %s", (selected_id,))
        prod = cursor.fetchone()
        
        with st.form("update_form"):
            new_preis = st.number_input("Neuer Preis (€)", value=float(prod[1]))
            new_json = st.text_area("Neue Attribute (JSON)", json.dumps(prod[2], indent=2) if prod[2] else "{}")
            
            if st.form_submit_button("Aktualisieren"):
                try:
                    updated_dict = json.loads(new_json)
                    cursor.execute(
                        "UPDATE produkte SET preis = %s, eigenschaften = %s WHERE id = %s",
                        (new_preis, json.dumps(updated_dict), selected_id)
                    )
                    st.success(f"Produkt {selected_id} aktualisiert!")
                    # st.rerun()
                except Exception as e:
                    st.error(f"Ungültiges JSON-Format: {e}")
    else:
        st.info("Keine Produkte zum Bearbeiten vorhanden.")

# 4. DELETE (Löschen)
with tab_delete:
    st.header("Produkt löschen")
    cursor.execute("SELECT id FROM produkte ORDER BY id")
    all_ids_del = [r[0] for r in cursor.fetchall()]
    
    if all_ids_del:
        delete_id = st.selectbox("Wähle eine ID zum Löschen", all_ids_del, key="del_select")
        if st.button("Endgültig löschen"):
            cursor.execute("DELETE FROM produkte WHERE id = %s", (delete_id,))
            st.warning(f"Produkt {delete_id} wurde gelöscht.")
            # st.rerun()
    else:
        st.info("Keine Produkte zum Löschen vorhanden.")