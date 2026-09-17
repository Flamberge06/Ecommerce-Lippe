import psycopg2

# Globale Verbindungs-Konfiguration
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "dbbpostger_123",
    "host": "localhost",
    "port": "5432"
}

def get_connection():
    """Erstellt eine neue Verbindung zur PostgreSQL-Datenbank."""
    return psycopg2.connect(**DB_CONFIG)