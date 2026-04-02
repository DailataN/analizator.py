import sqlite3
import pandas as pd


def load_table_from_db(db_path, table_name):
    try:
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Nieprawidłowa nazwa tabeli.")

        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

        return df
    except Exception as e:
        raise Exception(f"Błąd odczytu bazy danych: {e}")