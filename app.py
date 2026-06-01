from flask import Flask, render_template, request, redirect, session 
import mysql.connector
from bd import obter_ligacao

app = Flask(__name__)
app.secret_key = "01031315"

@app.route('/')
def inicio(): 
    return render_template('login.html')

@app.route('/login')
def login(): 
    return render_template('login.html')

#redireciona sempre para login se nao houver sessao iniciada
@app.route('/') 
def dashboard(): 
    if "user_id" not in session: 
        return redirect("/login") 
    return render_template( "index.html" ) 

#limpa as informações da sessão
@app.route('/logout')
def logout(): 
    session.clear()
    return redirect('/login')

@app.route('/perfil/<id>', methods = ["GET"])
def perfil(id):
    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("select * from utilizador where id = %s", (id))
    utili = cursor.fetchone()

    cursor.execute("select count(*) from elementocolecao where idUtilizador = %s", (id))
    numJogos = cursor.fetchone()
    
    cursor.close()
    bd.close()
    return render_template('perfil.html', utili=utili, numJogos = numJogos)


if __name__ == "__main__" :
    app.run(debug=True)
