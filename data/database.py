import sqlite3
import pandas as pd


def load_table_from_db(db_path, table_name):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        raise Exception(f"Blad odczytu bazy danych: {e}")