from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from bd import obter_ligacao
import hashlib
import re
from flask_session import Session
from typing import Any, cast

app = Flask(__name__)

# -- Rotas Principais e Sessão --------------------------------------

@app.route('/') 
def dashboard(): 
    # Unificação das rotas
    if "id" not in session: 
        return redirect("/login") 
    return redirect("/perfil") 

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect('/login')

# -- Login --------------------------------------------------------
@app.route('/login', methods=["POST", "GET"])
def login(): 
    if request.method == "POST":
        user_id = request.form["id"]
        senha = request.form["senha"]
        senha_hash = hashlib.sha256(senha.encode('utf-8')).hexdigest()

        bd = obter_ligacao()
        cursor = bd.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM utilizador WHERE id = %s", (user_id,))
        utilizador = cursor.fetchone()

        cursor.close()
        bd.close()

        if utilizador is None:
            flash("Utilizador não existe.", "erro")
        elif senha_hash != utilizador.get("senha"): 
            flash("Senha incorreta.", "erro")
        else:
            session["id"] = user_id
            session["tipoConta"] = utilizador.get("tipoConta")
            return redirect("/") # Correção

    return render_template('login.html')

# -- Criação de Conta ----------------------------------------------
@app.route('/criar-conta', methods=['GET', 'POST'])
def criarConta():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmarSenha', '')
    
        if len(nome) < 3:
            flash('O nome deve ter pelo menos 3 caracteres.', 'erro')
            return render_template('criarConta.html', form_data={'nome': nome, 'email': email})
        
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            flash('O email introduzido não é válido.', 'erro')
            return render_template('criarConta.html', form_data={'nome': nome, 'email': email})
        
        if senha != confirmar:
            flash('As duas senhas não coincidem.', 'erro')
            return render_template('criarConta.html', form_data={'nome': nome, 'email': email})
        
        bd = obter_ligacao()
        cursor = bd.cursor(dictionary=True)
        
        # Verificar se utilizador existe
        cursor.execute("SELECT id FROM utilizador WHERE id = %s", (nome,))
        if cursor.fetchone():
            flash('Este nome de utilizador já existe.', 'erro')
            cursor.close()
            bd.close()
            return render_template('criarConta.html', form_data={'nome': nome, 'email': email})
        
        # Verificar se email existe
        cursor.execute("SELECT id FROM utilizador WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Este email já está registado.', 'erro')
            cursor.close()
            bd.close()
            return render_template('criarConta.html', form_data={'nome': nome, 'email': email})
        
        # Inserir novo utilizador
        senha_hash = hashlib.sha256(senha.encode('utf-8')).hexdigest()
        cursor.execute(
            "INSERT INTO utilizador (id, email, senha, tipoConta, descricao) VALUES (%s, %s, %s, %s, %s)",
            (nome, email, senha_hash, '0', '')
        )
    
        bd.commit()
        cursor.close()
        bd.close()
        flash('Conta criada com sucesso!', 'sucesso')
        return redirect('/login')
        
    return render_template('criarConta.html', form_data=None)

# -- Perfil -------------------------------------------------------
@app.route('/perfil', methods=["GET"])
def perfil():
    # Proteção
    if "id" not in session:
        return redirect("/login")

    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM utilizador WHERE id = %s", (session["id"],))
    utili = cursor.fetchone()

    cursor.execute("SELECT count(*) AS total FROM elementocolecao WHERE idUtilizador = %s", (session["id"],))
    numJogos = cursor.fetchone()
    
    cursor.close()
    bd.close()
    return render_template('perfil.html', utili=utili, numJogos=numJogos)

if __name__ == "__main__":
    app.secret_key = "01031315"
    app.config['SESSION_TYPE'] = 'filesystem'
    sess = Session()
    sess.init_app(app)

    app.run(debug=True)
