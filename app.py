
from flask import Flask, request, render_template_string
import yfinance as yf

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bolsa IA</title>
<style>
body { font-family: Arial; background:#101827; color:white;
       margin:0; padding:20px; }
.card { background:#1e293b; padding:18px; margin:15px 0;
        border-radius:14px; }
input,button { padding:12px; border-radius:8px; border:0;
               margin:4px 0; }
button { background:#22c55e; color:#102015; font-weight:bold; }
input { width:90%; max-width:300px; }
h1 { color:#4ade80; }
</style>
</head>
<body>
<h1>📈 Bolsa IA</h1>
<p>Seu simulador de investimentos</p>

<div class="card">
<h3>Saldo fictício</h3>
<h2>R$ 10.000,00</h2>
<p>Modo de simulação — sem dinheiro real.</p>
</div>

<div class="card">
<h3>Consultar ações</h3>
<form method="get">
<input name="ticker" value="{{ ticker }}"
placeholder="Ex.: PETR4.SA">
<br>
<button type="submit">Consultar cotação</button>
</form>
{% if erro %}
<p>{{ erro }}</p>
{% elif preco %}
<h3>{{ ticker }}</h3>
<p>Último fechamento: R$ {{ preco }}</p>
<h3>Histórico recente</h3>
<ul>
{% for dia, valor in historico %}
<li>{{ dia }} — R$ {{ valor }}</li>
{% endfor %}
</ul>
{% endif %}
</div>
</body>
</html>
"""

@app.route("/")
def inicio():
    ticker = request.args.get("ticker", "PETR4.SA").upper().strip()
    preco = None
    historico = []
    erro = None

    if not ticker:
        erro = "Digite o código de uma ação."
    else:
        try:
            dados = yf.Ticker(ticker).history(period="1mo")
            if dados.empty:
                erro = "Não encontrei dados. Confira o código da ação."
            else:
                preco = f"{dados['Close'].iloc[-1]:.2f}"
                historico = [
                    (dia.strftime("%d/%m/%Y"), f"{valor:.2f}")
                    for dia, valor in dados["Close"].tail(10).items()
                ]
        except Exception:
            erro = "Não foi possível consultar os dados agora."

    return render_template_string(
        HTML, ticker=ticker, preco=preco,
        historico=historico, erro=erro
    )

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)))
              
