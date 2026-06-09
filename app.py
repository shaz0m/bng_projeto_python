from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
    numJogos = cursor.fetchone()["total"]
    
    cursor.close()
    bd.close()
    return render_template('perfil.html', utili=utili, numJogos=numJogos)

#--Homepage--------------------------------------------------------
@app.route('/home')
def home():
    if "id" not in session:
        return redirect("/login")
    
    import random
    from bd import fetch_all

    top10 = fetch_all(
        "SELECT id, nome, rankJogo, avaliacaoPublico FROM jogo ORDER BY rankJogo ASC LIMIT 10"
    )

    todos = fetch_all("SELECT id, nome, avaliacaoPublico FROM jogo")
    recomendacoes = random.sample(todos, min(3,len(todos)))

    return render_template('home.html', top10=top10, recomendacoes=recomendacoes, utili=session)



# -- Todos Jogos -------------------------------------------
@app.route('/todos-jogos', methods=["GET"])
def todosJogos():
     # Proteção
    if "id" not in session:
        return redirect("/login")
    
    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM utilizador WHERE id = %s", (session["id"],))
    utili = cursor.fetchone()

    cursor.execute("select * from jogo LIMIT 10")
    jogos = cursor.fetchall()

    cursor.execute("SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND favorito = 1", (session["id"],))
    favoritos_db = cursor.fetchall()
    favoritos = {row["idJogo"] for row in favoritos_db}

    cursor.execute("SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND jogado = 1", (session["id"],))
    jogados_db = cursor.fetchall()
    jogados = {row["idJogo"] for row in jogados_db}

    cursor.execute("SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND posse = 1", (session["id"],))
    possui_db = cursor.fetchall()
    possui = {row["idJogo"] for row in possui_db}

    cursor.execute("SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s", (session["id"],))
    colecao_db = cursor.fetchall()
    colecao = {row["idJogo"] for row in colecao_db}

    cursor.close()
    bd.close()

    return render_template("todosJogos.html", utili=utili, jogos = jogos, favoritos = favoritos, jogados = jogados, possui = possui, colecao = colecao)

# -- Filtrar Jogos -------------------------------------------
@app.route('/filtrar-jogos', methods=["GET"])
def filtrarJogos():
    if "id" not in session:
        return redirect("/login")
    
    filtros = request.args.getlist('filtro')
    pesquisa = request.args.get('pesquisa', '')

    sqlQuery = "SELECT * FROM jogo WHERE 1=1"
    parametros = []

    if(pesquisa):
        sqlQuery += " AND nome LIKE %s"
        parametros.append('%' + pesquisa + '%')

    if("favoritos" in filtros):
        sqlQuery += " AND id IN (SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND favorito = 1)"
        parametros.append(session["id"])

    if("jogados" in filtros):
        sqlQuery += " AND id IN (SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND jogado = 1)"
        parametros.append(session["id"])
    if("possui" in filtros):
        sqlQuery += " AND id IN (SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s AND posse = 1)"
        parametros.append(session["id"])

    if("colecao" in filtros):
        sqlQuery += " AND id IN (SELECT idJogo FROM elementocolecao WHERE idUtilizador = %s)"
        parametros.append(session["id"])


    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM utilizador WHERE id = %s", (session["id"],))
    utili = cursor.fetchone()

    cursor.execute(sqlQuery, tuple(parametros))
    jogos = cursor.fetchall()

    cursor.execute("SELECT idJogo, favorito, jogado, posse FROM elementocolecao WHERE idUtilizador = %s", (session["id"],))
    elementos = cursor.fetchall()

    favoritos = {row["idJogo"] for row in elementos if row["favorito"]}

    jogados = {row["idJogo"] for row in elementos if row["jogado"]}

    possui = {row["idJogo"] for row in elementos if row["posse"]}

    colecao = {row["idJogo"] for row in elementos}

    cursor.close()
    bd.close()

    return render_template("todosJogos.html", utili=utili, jogos=jogos, favoritos=favoritos, jogados=jogados, possui=possui, colecao=colecao, filtros=filtros, pesquisa=pesquisa
)

# -- Remover da Coleção -------------------------------------------
@app.route('/remover-colecao', methods=["POST"])
def removerColecao():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("DELETE FROM elementocolecao WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo removido da coleção.")
    return redirect("/todos-jogos")

# -- Adicionar à Coleção -------------------------------------------
@app.route('/adicionar-colecao', methods=["POST"])
def adicionarColecao():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("INSERT INTO elementocolecao (idUtilizador, idJogo, posse, jogado, favorito) VALUES (%s, %s, %s, %s, %s)", (session["id"], idJogo, 0, 0, 0))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo adicionado à coleção.")
    return redirect("/todos-jogos")

# -- Adicionar à Favoritos -------------------------------------------
@app.route('/adicionar-favoritos', methods=["POST"])
def adicionarFavoritos():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET favorito = 1 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo adicionado aos favoritos.")
    return redirect("/todos-jogos")

# -- Remover dos Favoritos -------------------------------------------
@app.route('/remover-favoritos', methods=["POST"])
def removerFavoritos():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET favorito = 0 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo removido dos favoritos.")
    return redirect("/todos-jogos")


# -- Adicionar à Posse -------------------------------------------
@app.route('/adicionar-posse', methods=["POST"])
def adicionarPosse():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET posse = 1 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo adicionado à posse.")
    return redirect("/todos-jogos")

# -- Remover da Posse -------------------------------------------
@app.route('/remover-posse', methods=["POST"])
def removerPosse():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET posse = 0 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo removido da posse.")
    return redirect("/todos-jogos")

# -- Adicionar à Jogados -------------------------------------------
@app.route('/adicionar-jogados', methods=["POST"])
def adicionarJogados():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET jogado = 1 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo adicionado aos jogados.")
    return redirect("/todos-jogos")

# -- Remover dos Jogados -------------------------------------------
@app.route('/remover-jogados', methods=["POST"])
def removerJogados():
    if "id" not in session:
        return redirect("/login")

    idJogo = request.form.get('jogo_id')

    bd = obter_ligacao()
    cursor = bd.cursor()

    cursor.execute("UPDATE elementocolecao SET jogado = 0 WHERE idUtilizador = %s AND idJogo = %s", (session["id"], idJogo))
    bd.commit()

    cursor.close()
    bd.close()

    flash("Jogo removido dos jogados.")
    return redirect("/todos-jogos")


# -----------------------------------------------------------------
#    API REST
# -----------------------------------------------------------------
# -- GETs ---------------------------------------------------------
@app.route("/api/utilizadores", methods=["GET"])
def apiListarUtilizadores():
    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM utilizador")
    utilizadores = cursor.fetchall()

    cursor.close()
    bd.close()

    return jsonify(utilizadores)

@app.route("/api/jogos", methods=["GET"])
def apiListarJogos():
    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM jogo")
    jogos = cursor.fetchall()

    cursor.close()
    bd.close()

    return jsonify(jogos)

@app.route("/api/elementoscolecao", methods=["GET"])
def apiListarElementosColecao():
    bd = obter_ligacao()
    cursor = bd.cursor(dictionary=True)

    cursor.execute("SELECT * FROM elementocolecao")
    elementosColecao = cursor.fetchall()

    cursor.close()
    bd.close()

    return jsonify(elementosColecao) 
# -----------------------------------------------------------------
# -- POSTs --------------------------------------------------------

# -----------------------------------------------------------------
# -- PUTs ---------------------------------------------------------

# -----------------------------------------------------------------
# -- DELETEs ------------------------------------------------------

# -----------------------------------------------------------------
if __name__ == "__main__":
    app.secret_key = "01031315"
    app.config['SESSION_TYPE'] = 'filesystem'
    sess = Session()
    sess.init_app(app)

    app.run(debug=True)

