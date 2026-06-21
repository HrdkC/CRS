# database/database.py

import sqlite3

from config.settings import DATABASE_PATH


def get_connection():

    conn = sqlite3.connect(DATABASE_PATH)

    conn.row_factory = sqlite3.Row

    return conn