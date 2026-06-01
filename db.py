import mysql.connector

def obter_ligacao():
    return mysql.connector.connect(
        host = '62.28.39.135',
        user = 'apdz0125',
        password = '123.Abc',
        database = 'apdz0125_gnb_projeto_python'
    )
