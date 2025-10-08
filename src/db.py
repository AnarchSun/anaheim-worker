import sqlite3
from sqlite3 import Error
import os
import datetime

DB_FILE = "db/anarcrypt.db"  # chemin du fichier SQLite
LOG_FILE = "db/db_errors.log"

# Assure que le dossier db existe
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def log_error(message):
    """Écrit une erreur SQL dans un fichier log"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {message}\n")


def create_connection(db_file=DB_FILE):
    """Crée une connexion SQLite"""
    try:
        connection = sqlite3.connect(db_file)
        print("Connexion SQLite OK. Version:", sqlite3.version)
        return connection
    except Error as e:
        log_error(f"Erreur de connexion: {e}")
        print("Erreur de connexion:", e)
        return None


def execute_query(connection, query, params=None):
    """Exécute une requête SQL avec la connexion passée"""
    try:
        cur = connection.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        connection.commit()
        return cur.fetchall()
    except Error as e:
        log_error(f"Erreur SQL: {e} | Query: {query} | Params: {params}")
        print("Erreur SQL:", e)
        return None


# -----------------------
# Helpers pour balances
# -----------------------

def create_table(connection):
    """Crée la table balances si elle n'existe pas"""
    query = """
            CREATE TABLE IF NOT EXISTS balances (
                                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                    address TEXT NOT NULL UNIQUE,
                                                    balance INTEGER NOT NULL
            ) \
            """
    execute_query(connection, query)


def insert_balance(connection, address, balance):
    """Insère une nouvelle adresse avec un solde"""
    query = "INSERT INTO balances (address, balance) VALUES (?, ?)"
    return execute_query(connection, query, (address, balance))


def update_balance(connection, address, balance):
    """Met à jour le solde d'une adresse existante"""
    query = "UPDATE balances SET balance = ? WHERE address = ?"
    return execute_query(connection, query, (balance, address))


def get_balance(connection, address):
    """Récupère le solde d'une adresse spécifique"""
    query = "SELECT balance FROM balances WHERE address = ?"
    rows = execute_query(connection, query, (address,))
    return rows[0][0] if rows else None


def get_all_balances(connection):
    """Retourne toutes les adresses et leurs soldes"""
    query = "SELECT address, balance FROM balances"
    return execute_query(connection, query)


def delete_balance(connection, address):
    """Supprime une adresse de la base"""
    query = "DELETE FROM balances WHERE address = ?"
    return execute_query(connection, query, (address,))


# -----------------------
# Script principal (test)
# -----------------------

if __name__ == "__main__":
    conn = create_connection()
    if conn:
        create_table(conn)

        # Exemple : insert + update + get
        insert_balance(conn, "So1anaAddress123", 500)
        update_balance(conn, "So1anaAddress123", 750)

        print("Balance unique:", get_balance(conn, "So1anaAddress123"))
        print("Toutes les balances:", get_all_balances(conn))

        # Exemple : suppression
        delete_balance(conn, "So1anaAddress123")
        print("Après suppression:", get_all_balances(conn))

        conn.close()


def export_json():
    return None


def get_fix():
    return None


def add_or_increment():
    return None


def init_db():
    return None