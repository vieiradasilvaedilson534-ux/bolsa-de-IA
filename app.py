
import os
import re
import yfinance as yf
from flask import Flask, request, redirect, url_for, render_template_string, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-simulador-bolsa-ia")

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bolsa IA</title>
<style>
* { box-sizing: border-box; }
body {
  margin: 0; padding: 18px; background: #0b1220;
  color: #e5e7eb; font-family: Arial, sans-serif;
}
main { max-width: 850px; margin: auto; }
h1 { color: #4ade80; }
.card {
  background: #172235; padding: 18px; margin: 16px 0;
  border-radius: 14px; border: 1px solid #29374d;
}
input, button {
  padding: 12px; margin: 5px 0; border-radius: 8px;
  border: 0; font-size: 16px; max-width: 100%;
}
input { width: 100%; background: #f1f5f9; }
button {
  background: #4ade80; color: #052e16;
  font-weight: bold; cursor: pointer;
}
.sell { background: #f87171; color: #450a0a; }
.green { color: #4ade80; }
.red { color: #f87171; }
.muted { color: #aab7ca; }
table { width: 100%; border-collapse: collapse; }
td, th {
  text-align: left; padding: 9px 5px;
  border-bottom: 1px solid #334155; font-size: 14px;
}
.table-wrap { overflow-x: auto; }
.notice { overflow-wrap: anywhere; }
</style>
</head>
<body>
<main>
<h1>📈 Bolsa IA</h1>
<p class="muted">Simulador de investimentos na B3</p>

<div class="card">
  <p>DINHEIRO FICTÍCIO DISPONÍVEL</p>
  <h2 class="green">R$ {{ saldo }}</h2>
  <p>Valor das ações: R$ {{ total_acoes }}</p>
  <p>Patrimônio simulado: <strong>R$ {{ patrimonio }}</strong></p>
  <p>Resultado das posições: <strong class="{{ 'green' if lucro_num >= 0 else 'red' }}">R$ {{ lucro }}</strong></p>
  <p class="muted">Nenhuma operação usa dinheiro real.</p>
</div>

{% with mensagens = get_flashed_messages() %}
  {% for mensagem in mensagens %}
    <div class="card notice">{{ mensagem }}</div>
  {% endfor %}
{% endwith %}

<div class="card">
<h3>Consultar ação</h3>
<form method="get">
  <input name="ticker" value="{{ ticker }}" placeholder="Ex.: PETR4.SA">
  <button type="submit">Consultar cotação</button>
</form>
{% if preco %}
  <h2>{{ ticker }}</h2>
  <p>Último fechamento: <strong class="green">R$ {{ preco }}</strong></p>
  <p class="muted">Os dados podem ter atraso e não representam necessariamente o preço em tempo real.</p>
  <h3>Histórico recente</h3>
  <div class="table-wrap">
  <table>
    <tr><th>Data</th><th>Fechamento</th></tr>
    {% for dia, valor in historico %}
      <tr><td>{{ dia }}</td><td>R$ {{ valor }}</td></tr>
    {% endfor %}
  </table>
  </div>
{% elif erro %}
  <p>{{ erro }}</p>
{% endif %}
</div>

<div class="card">
<h3>Comprar ações</h3>
<form method="post">
  <input type="hidden" name="acao" value="comprar">
  <input name="ticker" value="{{ ticker }}" placeholder="Código, ex.: PETR4.SA" required>
  <input name="quantidade" type="number" min="1" step="1" placeholder="Quantidade de ações" required>
  <button type="submit">Comprar com saldo fictício</button>
</form>
<p class="muted">A compra usa o último fechamento disponível, não uma cotação garantidamente em tempo real.</p>
</div>

<div class="card">
<h3>Vender ações</h3>
<form method="post">
  <input type="hidden" name="acao" value="vender">
  <input name="ticker" value="{{ ticker }}" placeholder="Código, ex.: PETR4.SA" required>
  <input name="quantidade" type="number" min="1" step="1" placeholder="Quantidade para vender" required>
  <button class="sell" type="submit">Vender ações simuladas</button>
</form>
</div>

<div class="card">
<h3>Minha carteira</h3>
{% if posicoes %}
<div class="table-wrap">
<table>
<tr><th>Ação</th><th>Qtd.</th><th>Preço</th><th>Valor</th><th>Resultado</th></tr>
{% for p in posicoes %}
<tr>
<td>{{ p.ticker }}</td>
<td>{{ p.qtd }}</td>
<td>R$ {{ p.preco }}</td>
<td>R$ {{ p.valor }}</td>
<td class="{{ 'green' if p.lucro_num >= 0 else 'red' }}">R$ {{ p.lucro }}</td>
</tr>
{% endfor %}
</table>
</div>
{% else %}
<p class="muted">Você ainda não tem ações. Faça uma compra simulada acima.</p>
{% endif %}
</div>

<p class="muted">Bolsa IA — ambiente educacional de simulação.</p>
</main>
</body>
</html>
"""

def dinheiro(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def cotacao(ticker, periodo="1mo"):
    dados = yf.Ticker(ticker).history(period=periodo)
    if dados.empty:
        return None, []
    preco = float(dados["Close"].iloc[-1])
    historico = [
        (dia.strftime("%d/%m/%Y"), dinheiro(float(valor)))
        for dia, valor in dados["Close"].tail(10).items()
    ]
    return preco, historico

@app.route("/", methods=["GET", "POST"])
def inicio():
    if "saldo" not in session:
        session["saldo"] = 10000.0
    if "carteira" not in session:
        session["carteira"] = {}

    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        operacao = request.form.get("acao", "")
        quantidade_texto = request.form.get("quantidade", "")

        if not re.fullmatch(r"[A-Z0-9]{4,7}\\.SA", ticker):
            flash("Código inválido. Use o formato PETR4.SA ou VALE3.SA.")
            return redirect(url_for("inicio"))

        try:
            quantidade = int(quantidade_texto)
            if quantidade < 1:
                raise ValueError()
        except (ValueError, TypeError):
            flash("Digite uma quantidade inteira maior que zero.")
            return redirect(url_for("inicio", ticker=ticker))

        try:
            preco, _ = cotacao(ticker, "5d")
            if preco is None:
                flash("Não encontrei essa ação. Confira o código e tente novamente.")
                return redirect(url_for("inicio", ticker=ticker))
        except Exception:
            flash("Não consegui consultar a cotação. Tente novamente mais tarde.")
            return redirect(url_for("inicio", ticker=ticker))

        saldo = float(session["saldo"])
        carteira = dict(session["carteira"])
        posicao = dict(carteira.get(ticker, {"qtd": 0, "medio": 0.0}))
        custo = preco * quantidade

        if operacao == "comprar":
            if custo > saldo:
                flash("Saldo fictício insuficiente para essa compra.")
            else:
                qtd_antiga = int(posicao["qtd"])
                qtd_nova = qtd_antiga + quantidade
                posicao["medio"] = (
                    (qtd_antiga * float(posicao["medio"]) + custo) / qtd_nova
                )
                posicao["qtd"] = qtd_nova
                carteira[ticker] = posicao
                session["saldo"] = round(saldo - custo, 2)
                session["carteira"] = carteira
                session.modified = True
                flash(f"Compra simulada: {quantidade} ação(ões) de {ticker}.")

        elif operacao == "vender":
            qtd_antiga = int(posicao["qtd"])
            if quantidade > qtd_antiga:
                flash("Você não possui essa quantidade de ações para vender.")
            else:
                posicao["qtd"] = qtd_antiga - quantidade
                session["saldo"] = round(saldo + custo, 2)
                if posicao["qtd"] == 0:
                    carteira.pop(ticker, None)
                else:
                    carteira[ticker] = posicao
                session["carteira"] = carteira
                session.modified = True
                flash(f"Venda simulada: {quantidade} ação(ões) de {ticker}.")
        else:
            flash("Operação inválida.")

        return redirect(url_for("inicio", ticker=ticker))

    ticker = request.args.get("ticker", "PETR4.SA").upper().strip()
    erro = None
    preco = None
    historico = []

    if re.fullmatch(r"[A-Z0-9]{4,7}\\.SA", ticker):
        try:
            preco, historico = cotacao(ticker)
            if preco is None:
                erro = "Não encontrei dados para esse código."
        except Exception:
            erro = "Não foi possível consultar os dados agora."
    else:
        erro = "Use o código de uma ação brasileira, como PETR4.SA."

    carteira = session["carteira"]
    posicoes = []
    total_acoes = 0.0
    lucro_total = 0.0

    for codigo, item in carteira.items():
        try:
            preco_atual, _ = cotacao(codigo, "5d")
            if preco_atual is None:
                continue
            qtd = int(item["qtd"])
            valor = preco_atual * qtd
            lucro_num = (preco_atual - float(item["medio"])) * qtd
            total_acoes += valor
            lucro_total += lucro_num
            posicoes.append({
                "ticker": codigo,
                "qtd": qtd,
                "preco": dinheiro(preco_atual),
                "valor": dinheiro(valor),
                "lucro": dinheiro(lucro_num),
                "lucro_num": lucro_num
            })
        except Exception:
            continue

    saldo = float(session["saldo"])
    return render_template_string(
        HTML,
        ticker=ticker,
        erro=erro,
        preco=dinheiro(preco) if preco is not None else None,
        historico=historico,
        saldo=dinheiro(saldo),
        total_acoes=dinheiro(total_acoes),
        patrimonio=dinheiro(saldo + total_acoes),
        lucro=dinheiro(lucro_total),
        lucro_num=lucro_total,
        posicoes=posicoes
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
               
