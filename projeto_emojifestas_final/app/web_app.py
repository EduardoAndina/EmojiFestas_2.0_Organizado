import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from flask import Flask, jsonify, render_template, request, session

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.banco import Banco
from models.entidades import CalendarioSalao
from ui.menu import (
    validar_data_festa,
    validar_e_formatar_celular,
    validar_e_formatar_cpf,
    validar_e_formatar_nome,
    validar_hora_festa,
)

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "web" / "templates"),
    static_folder=str(ROOT_DIR / "web" / "static"),
    static_url_path="/static",
)
app.secret_key = os.environ.get("SECRET_KEY", "emojifestas-poo-2026-secret")
db = Banco()


def listar_festas_detalhadas():
    resultado = []
    for festa in db.listar_festas():
        cliente = db.cliente(festa.cliente_id)
        salao = db.salao(festa.salao_id)
        combo = db.combo(festa.combo_id)
        pago = db.total_pago(festa.id)
        saldo = max(0.0, round(festa.total - pago, 2))
        resultado.append({
            "id": festa.id,
            "salao_id": festa.salao_id,
            "cliente_id": festa.cliente_id,
            "cliente_nome": cliente.nome if cliente else "Cliente não encontrado",
            "salao_nome": salao.nome if salao else "Espaço não encontrado",
            "titulo": f"Festa {combo.nome}" if combo else "Festa Personalizada",
            "data": festa.data,
            "inicio": festa.inicio,
            "fim": festa.hora_fim_str(),
            "duracao": festa.duracao,
            "combo_id": festa.combo_id,
            "combo_nome": combo.nome if combo else "Sem combo",
            "horas_extra": festa.horas_extra,
            "total": festa.total,
            "pago": pago,
            "restante": saldo,
            "obs": festa.obs,
            "extras": festa.extras,
        })
    return resultado


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/sessao")
def sessao_atual():
    user = session.get("usuario")
    return jsonify({"logado": bool(user), "usuario": user})


@app.post("/api/login")
def api_login():
    dados = request.get_json(silent=True) or {}
    usuario = str(dados.get("usuario", "")).strip()
    senha = str(dados.get("senha", "")).strip()
    func = db.autenticar(usuario, senha)
    if not func:
        return jsonify(error="Usuário ou senha inválidos."), 401
    user_data = {
        "id": func.id,
        "nome": func.nome,
        "usuario": func.usuario,
        "perfil": func.perfil,
        "eh_proprietaria": func.eh_proprietaria(),
    }
    session["usuario"] = user_data
    return jsonify(message=f"Bem-vindo(a), {func.nome}!", usuario=user_data)


@app.post("/api/logout")
def api_logout():
    session.pop("usuario", None)
    return jsonify(message="Sessão encerrada.")


@app.get("/api/dashboard")
def dashboard():
    festas = listar_festas_detalhadas()
    clientes = db.listar_clientes()
    recebido = sum(float(f["pago"] or 0) for f in festas)
    contratado = sum(float(f["total"] or 0) for f in festas)
    return jsonify({
        "total_festas": len(festas),
        "total_clientes": len(clientes),
        "valor_contratado": contratado,
        "valor_recebido": recebido,
        "valor_pendente": max(0.0, round(contratado - recebido, 2)),
    })


@app.get("/api/saloes")
def saloes():
    return jsonify([
        {
            "id": s.id,
            "nome": s.nome,
            "capacidade": s.capacidade,
            "acrescimo": s.acrescimo,
            "endereco": s.endereco,
            "diferencial": s.diferencial,
            "estrutura": s.estrutura,
        }
        for s in db.listar_saloes()
    ])


@app.post("/api/saloes")
def criar_salao():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    endereco = str(dados.get("endereco", "")).strip()
    diferencial = str(dados.get("diferencial", "")).strip()
    estrutura = str(dados.get("estrutura", "")).strip()
    try:
        capacidade = int(dados.get("capacidade"))
        acrescimo = float(dados.get("acrescimo", 0))
        sid = db.criar_salao(nome, capacidade, acrescimo, endereco, diferencial, estrutura)
        return jsonify(message="Espaço cadastrado com sucesso!", id=sid), 201
    except (TypeError, ValueError) as err:
        return jsonify(error=str(err) or "Verifique os dados do espaço."), 400


@app.get("/api/calendario")
def calendario_salao():
    try:
        salao_id = int(request.args.get("salao_id", 1))
        hoje = date.today()
        ano = int(request.args.get("ano", hoje.year))
        mes = int(request.args.get("mes", hoje.month))
        salao = db.salao(salao_id)
        if not salao:
            return jsonify(error="Espaço não encontrado."), 404
        festas_mes = db.listar_festas_por_salao_e_mes(salao_id, ano, mes)
        cal = CalendarioSalao(salao, ano, mes, festas_mes)
        reservas = []
        for f in cal.festas_mes:
            cli = db.cliente(f.cliente_id)
            reservas.append({
                "id": f.id,
                "dia": int(f.data.split("-")[2]),
                "data": f.data,
                "inicio": f.inicio,
                "fim": f.hora_fim_str(),
                "cliente_nome": cli.nome if cli else "Cliente",
            })
        return jsonify({
            "salao_id": salao.id,
            "salao_nome": salao.nome,
            "ano": ano,
            "mes": mes,
            "nome_mes": cal.nome_mes,
            "dia_inicio_semana": cal.dia_inicio_semana,
            "total_dias": cal.total_dias,
            "dias_ocupados": sorted(list(cal.dias_ocupados.keys())),
            "reservas": reservas,
            "grade_ascii": cal(),
        })
    except ValueError as err:
        return jsonify(error=str(err)), 400


@app.get("/api/combos")
def combos():
    return jsonify([
        {"id": c.id, "nome": c.nome, "preco": c.preco, "descricao": c.descricao}
        for c in db.listar_combos()
    ])


@app.get("/api/extras")
def extras():
    return jsonify([{"id": e.id, "nome": e.nome, "preco": e.preco} for e in db.listar_extras()])


@app.get("/api/clientes")
def clientes():
    return jsonify([
        {"id": c.id, "nome": c.nome, "contato": c.contato, "documento": c.documento}
        for c in db.listar_clientes()
    ])


@app.post("/api/clientes")
def criar_cliente():
    dados = request.get_json(silent=True) or {}
    ok_nome, nome_fmt = validar_e_formatar_nome(str(dados.get("nome", "")))
    if not ok_nome:
        return jsonify(error=nome_fmt), 400
    ok_cel, cel_fmt = validar_e_formatar_celular(str(dados.get("contato", "")))
    if not ok_cel:
        return jsonify(error=cel_fmt), 400
    ok_cpf, cpf_fmt = validar_e_formatar_cpf(str(dados.get("documento", "")))
    if not ok_cpf:
        return jsonify(error=cpf_fmt), 400

    cid = db.cadastrar_cliente(nome_fmt, cel_fmt, cpf_fmt)
    return jsonify(message=f"Cliente '{nome_fmt}' cadastrado com sucesso!", id=cid), 201


@app.get("/api/festas")
def festas():
    return jsonify(listar_festas_detalhadas())


@app.post("/api/festas")
def criar_festa():
    dados = request.get_json(silent=True) or {}
    try:
        salao_id = int(dados["salao_id"])
        cliente_id = int(dados["cliente_id"])
        ok_dt, data_fmt = validar_data_festa(str(dados.get("data", "")))
        if not ok_dt:
            return jsonify(error=data_fmt), 400
        ok_hr, hora_fmt = validar_hora_festa(str(dados.get("inicio", "")))
        if not ok_hr:
            return jsonify(error=hora_fmt), 400
        combo_id = int(dados["combo_id"]) if dados.get("combo_id") not in (None, "") else None
        horas_extra = int(dados.get("horas_extra", 0))
        extras_ids = [int(x) for x in dados.get("extras_ids", [])]
        obs = str(dados.get("obs", ""))
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Confira os dados do agendamento, a data e o horário."), 400

    sucesso, mensagem = db.agendar_festa(
        salao_id, cliente_id, data_fmt, hora_fmt, combo_id, extras_ids, horas_extra, obs
    )
    if not sucesso:
        return jsonify(error=mensagem), 409
    return jsonify(message=mensagem), 201


@app.delete("/api/festas/<int:festa_id>")
def deletar_festa(festa_id: int):
    sucesso, mensagem = db.cancelar_festa(festa_id)
    if not sucesso:
        return jsonify(error=mensagem), 404
    return jsonify(message=mensagem)


@app.get("/api/pagamentos")
def pagamentos():
    rows = db.conn.execute("""
        SELECT p.id, p.festa_id, p.valor, p.data, p.tipo,
               c.nome AS cliente_nome, f.data AS data_festa, s.nome AS salao_nome
        FROM pagamentos p
        LEFT JOIN festas f ON f.id = p.festa_id
        LEFT JOIN clientes c ON c.id = f.cliente_id
        LEFT JOIN saloes s ON s.id = f.salao_id
        ORDER BY p.data DESC, p.id DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/pagamentos")
def criar_pagamento():
    dados = request.get_json(silent=True) or {}
    try:
        festa_id = int(dados["festa_id"])
        valor_texto = str(dados["valor"]).strip().replace("R$", "").replace(" ", "")
        if "." in valor_texto and "," in valor_texto:
            valor_texto = (
                valor_texto.replace(".", "").replace(",", ".")
                if valor_texto.rfind(",") > valor_texto.rfind(".")
                else valor_texto.replace(",", "")
            )
        elif "," in valor_texto:
            valor_texto = valor_texto.replace(",", ".")
        valor_decimal = Decimal(valor_texto).quantize(Decimal("0.01"))
        valor = float(valor_decimal)
        data_pagamento = str(dados.get("data", date.today().isoformat()))
        datetime.strptime(data_pagamento, "%Y-%m-%d")
        tipo = str(dados.get("tipo", "Parcela")).strip() or "Parcela"
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return jsonify(error="Informe evento, valor válido e data válida."), 400

    sucesso, mensagem = db.registrar_pagamento(festa_id, valor, tipo, data_pagamento)
    if not sucesso:
        return jsonify(error=mensagem), 400
    return jsonify(message=mensagem), 201


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
