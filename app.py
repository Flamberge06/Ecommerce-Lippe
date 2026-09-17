import json
import psycopg2
import pandas as pd
import streamlit as st

# --- DB-VERBINDUNG ---
def get_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="dbbpostger_123",
        host="localhost",
        port="5432"
    )

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

# --- STREAMLIT TABS FOR CRUD ---
tab_read, tab_create, tab_update, tab_delete = st.tabs(["READ (Anzeigen)", "CREATE (Erstellen)", "UPDATE (Bearbeiten)", "DELETE (Löschen)"])

# 1. READ (Anzeigen)
with tab_read:
    st.header("Aktuelle Produkte")
    cursor.execute("SELECT id, kategorie, preis, eigenschaften FROM produkte")
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
        p_id = st.text_input("Produkt-ID (z. B. B011 oder T001)")
        kategorie = st.selectbox("Kategorie", ["Bücher", "Bekleidung", "Tabletop", "Sammelkarten"])
        preis = st.number_input("Preis (€)", min_value=0.0, step=0.5)
        json_input = st.text_area("Flexible Attribute (als JSON)", '{"titel": "Clean Code", "isbn": "978-0132350884"}')
        
        submitted = st.form_submit_button("Produkt speichern")
        if submitted:
            try:
                attr_dict = json.loads(json_input)
                cursor.execute(
                    "INSERT INTO produkte (id, kategorie, preis, eigenschaften) VALUES (%s, %s, %s, %s)",
                    (p_id, kategorie, preis, json.dumps(attr_dict))
                )
                st.success(f"Produkt {p_id} erfolgreich gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

# 3. UPDATE (Bearbeiten)
with tab_update:
    st.header("Produkt-Preis oder Attribute aktualisieren")
    cursor.execute("SELECT id FROM produkte")
    all_ids = [r[0] for r in cursor.fetchall()]
    
    if all_ids:
        selected_id = st.selectbox("Wähle eine ID zum Bearbeiten", all_ids)
        cursor.execute("SELECT kategorie, preis, eigenschaften FROM produkte WHERE id = %s", (selected_id,))
        prod = cursor.fetchone()
        
        with st.form("update_form"):
            new_preis = st.number_input("Neuer Preis (€)", value=float(prod[1]))
            new_json = st.text_area("Neue Attribute (JSON)", json.dumps(prod[2], indent=2))
            
            if st.form_submit_button("Aktualisieren"):
                cursor.execute(
                    "UPDATE produkte SET preis = %s, eigenschaften = %s WHERE id = %s",
                    (new_preis, new_json, selected_id)
                )
                st.success(f"Produkt {selected_id} aktualisiert!")
                st.rerun()

# 4. DELETE (Löschen)
with tab_delete:
    st.header("Produkt löschen")
    if all_ids:
        delete_id = st.selectbox("Wähle eine ID zum Löschen", all_ids, key="del_select")
        if st.button("Endgültig löschen"):
            cursor.execute("DELETE FROM produkte WHERE id = %s", (delete_id,))
            st.warning(f"Produkt {delete_id} wurde gelöscht.")
            st.rerun()