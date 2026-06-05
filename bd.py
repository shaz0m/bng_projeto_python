import mysql.connector

def obter_ligacao():
    return mysql.connector.connect(
        host = '62.28.39.135',
        user = 'apdz0125',
        password = '123.Abc',
        database = 'apdz0125_gnb_projeto_python'
    )

def fetch_all(query, params=None):
    conn = obter_ligacao()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()