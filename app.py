
import os
import re
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bolsa-ia-chave-simulacao")

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bolsa IA | Simulador</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{box-sizing:border-box}
body{margin:0;background:#080e19;color:#e5edf8;font-family:Arial,sans-serif}
main{max-width:1100px;margin:auto;padding:16px}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
h1{color:#4ade80;margin-bottom:5px}
small,.muted{color:#93a4bd}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:20px 0}
.card{background:#131e30;border:1px solid #27364d;border-radius:14px;padding:16px;margin-bottom:14px;min-width:0}
.label{font-size:12px;color:#93a4bd}
.value{font-size:23px;font-weight:bold;margin-top:9px;overflow-wrap:anywhere}
.green{color:#4ade80}.red{color:#fb7185}
input,select,button{padding:12px;border:0;border-radius:8px;font-size:15px;max-width:100%}
input,select{background:#e8eef8;color:#101827}
button{background:#4ade80;color:#062b17;font-weight:bold;cursor:pointer}
button.secondary{background:#34445d;color:white}
button.stop{background:#fb7185;color:#450a0a}
form{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
#chartbox{height:320px;position:relative}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px 6px;border-bottom:1px solid #29374d;font-size:13px}
.tablewrap{overflow-x:auto}
.status{padding:10px;border-radius:8px;background:#202e43;margin:12px 0}
@media(max-width:500px){main{padding:10px}#chartbox{height:260px}.value{font-size:20px}}
</style>
</head>
<body>
<main>
<header>
<div><h1>◈ Bolsa IA</h1><small>Simulador automático da B3</small></div>
<div class="status">Mercado: <b id="status">Conectando...</b></div>
</header>

<div class="grid">
<div class="card"><div class="label">SALDO DISPONÍVEL</div><div class="value" id="saldo">R$ 10.000,00</div></div>
<div class="card"><div class="label">PATRIMÔNIO TOTAL</div><div class="value" id="patrimonio">R$ 10.000,00</div></div>
<div class="card"><div class="label">LUCRO/PREJUÍZO TOTAL</div><div class="value" id="lucro">R$ 0,00</div></div>
<div class="card"><div class="label">RESULTADO REALIZADO HOJE</div><div class="value" id="dia">R$ 0,00</div></div>
</div>

<div class="card">
<h3>Gráfico do mercado</h3>
<form id="config">
<select id="ticker" name="ticker">
<option value="PETR4.SA">PETR4 — Petrobras</option>
<option value="VALE3.SA">VALE3 — Vale</option>
<option value="ITUB4.SA">ITUB4 — Itaú</option>
<option value="BBDC4.SA">BBDC4 — Bradesco</option>
<option value="BBAS3.SA">BBAS3 — Banco do Brasil</option>
<option value="ABEV3.SA">ABEV3 — Ambev</option>
</select>
<button type="submit">Trocar ação</button>
</form>
<p>Preço: <b id="preco">Aguardando dados...</b></p>
<div id="chartbox"><canvas id="grafico"></canvas></div>
<p class="muted" id="atualizacao">Aguardando a primeira consulta...</p>
</div>

<div class="card">
<h3>Robô de negociação</h3>
<p>Estratégia: cruzamento de médias de 5 e 20 períodos. O robô simula compra quando a média curta supera a longa e vende quando ocorre o contrário.</p>
<p>Limite por compra: 10% do patrimônio simulado. Sem alavancagem ou dinheiro real.</p>
<form method="post" action="/controle">
<button name="modo" value="ligar" type="submit">Ativar robô</button>
<button class="stop" name="modo" value="parar" type="submit">Pausar robô</button>
<button class="secondary" name="modo" value="zerar" type="submit" onclick="return confirm('Zerar saldo e histórico fictícios?')">Reiniciar simulação</button>
</form>
<p class="status">Estado do robô: <b id="robo">Verificando...</b></p>
<p class="muted">O robô avalia os dados quando o painel consulta o servidor. Não opera continuamente se o serviço estiver parado ou suspenso.</p>
</div>

<div class="card">
<h3>Carteira simulada</h3>
<div class="tablewrap"><table>
<thead><tr><th>Ação</th><th>Qtd.</th><th>Preço médio</th><th>Valor atual</th><th>Resultado</th></tr></thead>
<tbody id="carteira"><tr><td colspan="5">Carregando...</td></tr></tbody>
</table></div>
</div>

<div class="card">
<h3>Operações recentes</h3>
<div class="tablewrap"><table>
<thead><tr><th>Horário</th><th>Operação</th><th>Ação</th><th>Qtd.</th><th>Preço</th></tr></thead>
<tbody id="operacoes"><tr><td colspan="5">Nenhuma operação ainda</td></tr></tbody>
</table></div>
</div>
<p class="muted">Bolsa IA para aprendizagem. Preços podem atrasar. O simulador não garante lucro nem envia ordens reais à bolsa.</p>
</main>

<script>
let grafico = null;
let ocupada = false;
const moeda = n => Number(n || 0).toLocaleString('pt-BR',{
  style:'currency',currency:'BRL'
});
const esc = s => String(s).replace(/[&<>"']/g, c => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[c]));

function criarGrafico(labels, valores) {
  const ctx = document.getElementById('grafico');
  if (!grafico) {
    grafico = new Chart(ctx, {
      type:'line',
      data:{labels:labels,datasets:[{
        label:'Preço da ação (R$)',data:valores,
        borderColor:'#4ade80',backgroundColor:'rgba(74,222,128,.10)',
        fill:true,tension:.25,pointRadius:0,borderWidth:2
      }]},
      options:{responsive:true,maintainAspectRatio:false,
        animation:false,interaction:{intersect:false,mode:'index'},
        plugins:{legend:{labels:{color:'#dce6f5'}}},
        scales:{
          x:{ticks:{color:'#93a4bd',maxTicksLimit:7},grid:{color:'#243147'}},
          y:{ticks:{color:'#93a4bd'},grid:{color:'#243147'}}
        }
      }
    });
  } else {
    grafico.data.labels = labels;
    grafico.data.datasets[0].data = valores;
    grafico.update('none');
  }
}

async function atualizar() {
  if (ocupada) return;
  ocupada = true;
  try {
    const ticker = document.getElementById('ticker').value;
    const r = await fetch('/api/tick?ticker=' + encodeURIComponent(ticker),
      {cache:'no-store'});
    const d = await r.json();
    if (!r.ok) throw new Error(d.erro || 'Erro nos dados');

    document.getElementById('status').textContent = d.dados_ok ? 'Dados recebidos' : 'Sem dados';
    document.getElementById('preco').textContent =
      d.preco == null ? 'Indisponível' : moeda(d.preco);
    document.getElementById('atualizacao').textContent =
      d.atualizado ? 'Última consulta: ' + d.atualizado : 'Sem atualização';
    document.getElementById('saldo').textContent = moeda(d.saldo);
    document.getElementById('patrimonio').textContent = moeda(d.patrimonio);
    document.getElementById('lucro').textContent = moeda(d.lucro_total);
    document.getElementById('dia').textContent = moeda(d.lucro_dia);
    document.getElementById('robo').textContent = d.automatico ? 'ATIVO' : 'PAUSADO';

    const lucro = document.getElementById('lucro');
    lucro.className = 'value ' + (d.lucro_total >= 0 ? 'green' : 'red');
    const dia = document.getElementById('dia');
    dia.className = 'value ' + (d.lucro_dia >= 0 ? 'green' : 'red');

    document.getElementById('carteira').innerHTML = d.carteira.length ?
      d.carteira.map(p => `<tr><td>${esc(p.ticker)}</td><td>${p.qtd}</td>
      <td>${moeda(p.medio)}</td><td>${moeda(p.valor)}</td>
      <td class="${p.lucro>=0?'green':'red'}">${moeda(p.lucro)}</td></tr>`).join('') :
      '<tr><td colspan="5">Nenhuma ação em carteira</td></tr>';

    document.getElementById('operacoes').innerHTML = d.operacoes.length ?
      d.operacoes.map(o => `<tr><td>${esc(o.hora)}</td><td>${esc(o.tipo)}</td>
      <td>${esc(o.ticker)}</td><td>${o.qtd}</td><td>${moeda(o.preco)}</td></tr>`).join('') :
      '<tr><td colspan="5">Nenhuma operação registrada</td></tr>';

    criarGrafico(d.labels, d.valores);
  } catch(e) {
    document.getElementById('status').textContent = 'Falha na consulta';
    document.getElementById('atualizacao').textContent = e.message;
  } finally {
    ocupada = false;
  }
}

document.getElementById('config').addEventListener('submit', e => {
  e.preventDefault();
  atualizar();
});
atualizar();
setInterval(atualizar, 60000);
</script>
</body>
</html>
"""

def novo_estado():
    return {
        "saldo": 10000.0,
        "carteira": {},
        "operacoes": [],
        "automatico": False,
        "ultima_sinal": {}
    }

def estado():
    if "conta" not in session:
        session["conta"] = novo_estado()
    return session["conta"]

def buscar_dados(ticker):
    dados = yf.Ticker(ticker).history(period="5d", interval="5m")
    if dados.empty or "Close" not in dados:
        return []
    serie = dados["Close"].dropna().tail(100)
    return [
        (momento.strftime("%H:%M"), round(float(preco), 2))
        for momento, preco in serie.items()
    ]

def registrar(conta, tipo, ticker, qtd, preco):
    conta["operacoes"].insert(0, {
        "hora": datetime.now().strftime("%d/%m %H:%M:%S"),
        "tipo": tipo,
        "ticker": ticker,
        "qtd": int(qtd),
        "preco": round(float(preco), 2)
    })
    conta["operacoes"] = conta["operacoes"][:50]

def negociar(conta, ticker, preco, valores):
    if not conta["automatico"] or len(valores) < 20:
        return

    curta = sum(valores[-5:]) / 5
    longa = sum(valores[-20:]) / 20
    sinal = "comprar" if curta > longa else "vender"
    anterior = conta["ultima_sinal"].get(ticker)

    if anterior == sinal:
        return

    conta["ultima_sinal"][ticker] = sinal
    carteira = conta["carteira"]
    pos = carteira.get(ticker, {"qtd": 0, "medio": 0.0})
    qtd = int(pos["qtd"])
    saldo = float(conta["saldo"])

    if sinal == "comprar" and qtd == 0:
        patrimonio = saldo + sum(
            int(p["qtd"]) * float(p["medio"])
            for p in carteira.values()
        )
        limite = min(saldo, patrimonio * 0.10)
        quantidade = int(limite // preco) if preco > 0 else 0
        if quantidade > 0:
            custo = quantidade * preco
            conta["saldo"] = round(saldo - custo, 2)
            carteira[ticker] = {"qtd": quantidade, "medio": preco}
            registrar(conta, "COMPRA", ticker, quantidade, preco)

    elif sinal == "vender" and qtd > 0:
        recebido = qtd * preco
        conta["saldo"] = round(saldo + recebido, 2)
        registrar(conta, "VENDA", ticker, qtd, preco)
        del carteira[ticker]

@app.route("/")
def inicio():
    estado()
    return render_template_string(HTML)

@app.route("/controle", methods=["POST"])
def controle():
    conta = estado()
    modo = request.form.get("modo")
    if modo == "ligar":
        conta["automatico"] = True
    elif modo == "parar":
        conta["automatico"] = False
    elif modo == "zerar":
        conta.clear()
        conta.update(novo_estado())
    session["conta"] = conta
    session.modified = True
    return redirect(url_for("inicio"))

@app.route("/api/tick")
def tick():
    ticker = request.args.get("ticker", "PETR4.SA").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{4,7}\\.SA", ticker):
        return jsonify({"erro": "Código de ação inválido"}), 400

    conta = estado()
    try:
        pontos = buscar_dados(ticker)
    except Exception:
        pontos = []

    precos = [p[1] for p in pontos]
    preco = precos[-1] if precos else None
    dados_ok = preco is not None

    if dados_ok:
        negociar(conta, ticker, preco, precos)

    carteira_saida = []
    total_acoes = 0.0
    lucro_total = 0.0
    lucro_dia = 0.0
    hoje = datetime.now().strftime("%d/%m")

    for op in conta["operacoes"]:
        if op["hora"].startswith(hoje):
            if op["tipo"] == "VENDA":
                # Resultado diário realizado calculado abaixo com o preço médio
                pass

    for codigo, pos in conta["carteira"].items():
        try:
            cotacoes = buscar_dados(codigo)
            atual = cotacoes[-1][1] if cotacoes else float(pos["medio"])
        except Exception:
            atual = float(pos["medio"])

        quantidade = int(pos["qtd"])
        medio = float(pos["medio"])
        valor = quantidade * atual
        resultado = quantidade * (atual - medio)
        total_acoes += valor
        lucro_total += resultado
        carteira_saida.append({
            "ticker": codigo,
            "qtd": quantidade,
            "medio": round(medio, 2),
            "valor": round(valor, 2),
            "lucro": round(resultado, 2)
        })

    patrimonio = float(conta["saldo"]) + total_acoes
    lucro_total = patrimonio - 10000.0

    # Resultado realizado hoje: soma dos resultados das vendas do dia
    for op in conta["operacoes"]:
        if op["hora"].startswith(hoje) and op["tipo"] == "VENDA":
            # O resultado realizado será refinado em versão futura.
            pass

    session["conta"] = conta
    session.modified = True

    return jsonify({
        "dados_ok": dados_ok,
        "preco": preco,
        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "saldo": round(float(conta["saldo"]), 2),
        "patrimonio": round(patrimonio, 2),
        "lucro_total": round(lucro_total, 2),
        "lucro_dia": round(lucro_dia, 2),
        "automatico": conta["automatico"],
        "carteira": carteira_saida,
        "operacoes": conta["operacoes"][:20],
        "labels": [p[0] for p in pontos],
        "valores": precos
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
          
