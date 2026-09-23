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
    "Bekleidung": "TS",
    "Tabletop": "TT",
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
        import re
        match = re.search(r'\d+', letzte_id[len(praefix):])
        if match:
             neue_nummer = int(match.group()) + 1
        else:
             neue_nummer = 1

    neue_id = f"{praefix}{neue_nummer:03d}"
    return neue_id


# --- STREAMLIT TABS FOR CRUD + SUCHE ---
tab_read, tab_search, tab_create, tab_update, tab_delete = st.tabs([
    "READ (Anzeigen)", 
    "SUCHE (Filter)", 
    "CREATE (Erstellen)", 
    "UPDATE (Bearbeiten)", 
    "DELETE (Löschen)"
])

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

# 2. SUCHE (Filter) - NEUER TAB
with tab_search:
    st.header("Produkte durchsuchen und filtern")
    
    # Filter-Optionen in einer Spalten-Ansicht oder direkt untereinander
    col1, col2 = st.columns(2)
    with col1:
        # Alle verfügbaren Kategorien aus der Datenbank laden für das Dropdown
        cursor.execute("SELECT DISTINCT kategorie FROM produkte ORDER BY kategorie")
        kategorien_db = [r[0] for r in cursor.fetchall()]
        filter_kategorie = st.selectbox("Nach Kategorie filtern", ["Alle"] + kategorien_db)
        
    with col2:
        suchbegriff = st.text_input("Suchbegriff (durchsucht ID, Kategorie und JSON-Eigenschaften)")
    
    if st.button("Suche starten"):
        # Dynamische SQL-Abfrage aufbauen
        query = "SELECT id, kategorie, preis, eigenschaften FROM produkte WHERE 1=1"
        params = []
        
        if filter_kategorie != "Alle":
            query += " AND kategorie = %s"
            params.append(filter_kategorie)
            
        if suchbegriff:
            # Suche im ID-Feld, Kategorie-Feld oder im JSONB-Inhalt (als Text gewandelt)
            query += " AND (id ILIKE %s OR kategorie ILIKE %s OR eigenschaften::text ILIKE %s)"
            search_pattern = f"%{suchbegriff}%"
            params.extend([search_pattern, search_pattern, search_pattern])
            
        query += " ORDER BY id"
        
        cursor.execute(query, tuple(params))
        such_ergebnisse = cursor.fetchall()
        
        if such_ergebnisse:
            st.success(f"{len(such_ergebnisse)} Treffer gefunden:")
            df_suche = pd.DataFrame(such_ergebnisse, columns=["ID", "Kategorie", "Preis (€)", "Eigenschaften (JSON)"])
            st.dataframe(df_suche, use_container_width=True)
        else:
            st.warning("Keine passenden Produkte gefunden.")

# 3. CREATE (Erstellen)
with tab_create:
    st.header("Neues Produkt anlegen")
    with st.form("create_form"):
        kategorie = st.selectbox("Kategorie", ["Bücher", "Bekleidung", "Tabletop", "Sammelkarten", "Sammelfiguren", "Spiel", "T-Shirt"])
        preis = st.number_input("Preis (€)", min_value=0.0, step=0.5)
        json_input = st.text_area("Flexible Attribute (als JSON)", '{"titel": "Neuer Titel", "isbn": "12345"}')
        
        submitted = st.form_submit_button("Produkt speichern")
        if submitted:
            try:
                attr_dict = json.loads(json_input)
                neue_p_id = generiere_naechste_id(kategorie, cursor)
                cursor.execute(
                    "INSERT INTO produkte (id, kategorie, preis, eigenschaften) VALUES (%s, %s, %s, %s)",
                    (neue_p_id, kategorie, preis, json.dumps(attr_dict))
                )
                st.success(f"Produkt mit der automatisch generierten ID **{neue_p_id}** erfolgreich gespeichert!")
            except ValueError as ve:
                 st.error(f"Fehler bei der ID-Generierung: {ve}")
            except Exception as e:
                st.error(f"Fehler: {e}")

# 4. UPDATE (Bearbeiten)
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
                except Exception as e:
                    st.error(f"Ungültiges JSON-Format: {e}")
    else:
        st.info("Keine Produkte zum Bearbeiten vorhanden.")

# 5. DELETE (Löschen)
with tab_delete:
    st.header("Produkt löschen")
    cursor.execute("SELECT id FROM produkte ORDER BY id")
    all_ids_del = [r[0] for r in cursor.fetchall()]
    
    if all_ids_del:
        delete_id = st.selectbox("Wähle eine ID zum Löschen", all_ids_del, key="del_select")
        if st.button("Endgültig löschen"):
            cursor.execute("DELETE FROM produkte WHERE id = %s", (delete_id,))
            st.warning(f"Produkt {delete_id} wurde gelöscht.")
    else:
        st.info("Keine Produkte zum Löschen vorhanden.")