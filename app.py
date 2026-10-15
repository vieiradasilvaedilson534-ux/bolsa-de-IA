import os
import re
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-no-render")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

INITIAL_BALANCE = 10000.0
ALLOWED_TICKERS = {"PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "WEGE3.SA", "MGLU3.SA"}

HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Bolsa IA — Simulador</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{color-scheme:dark;--bg:#07111f;--panel:#111e30;--line:#263850;--text:#e8effa;--muted:#9aabc2;--green:#4ade80;--red:#fb7185;--blue:#93c5fd}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Arial,sans-serif}
main{width:min(1120px,100%);margin:auto;padding:clamp(10px,3vw,20px)}header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:4px 0 14px}
h1{margin:0;color:var(--green);font-size:clamp(24px,5vw,31px)}h2{font-size:19px;margin:0 0 14px}h3{font-size:16px}.muted,small{color:var(--muted)}.muted{line-height:1.55}
.pill{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:#1b2c42;color:var(--blue);font-size:12px;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0 18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:clamp(12px,2.5vw,18px);margin-bottom:14px;min-width:0;box-shadow:0 5px 20px #0000000a}
.label{font-size:11px;color:var(--muted);letter-spacing:.45px;font-weight:700}.value{font-size:clamp(19px,2.4vw,27px);font-weight:800;margin-top:8px;overflow-wrap:anywhere}
.green{color:var(--green)}.red{color:var(--red)}.muted{font-size:13px}
form.controls{display:flex;flex-wrap:wrap;align-items:center;gap:9px}
input,select,button{border:0;border-radius:10px;padding:12px;font-size:15px;max-width:100%;min-height:44px}
input,select{background:#e9f0fb;color:#101827}select{flex:1 1 210px;min-width:0}
button{background:var(--green);color:#062b17;font-weight:750;cursor:pointer;touch-action:manipulation}
button.secondary{background:#35465f;color:#fff}button.stop{background:var(--red);color:#450a0a}button:focus-visible,select:focus-visible{outline:3px solid var(--blue);outline-offset:2px}
#chartbox{height:clamp(240px,45vw,350px);position:relative;margin-top:10px}.status{padding:10px 12px;border-radius:10px;background:#1b2b40;margin:12px 0}
.notice{border:1px solid #6b4c1c;background:#302515;color:#fbd38d;border-radius:12px;padding:12px 14px;line-height:1.5;font-size:13px;margin:4px 0 14px}
.robot-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}
.robot-state{padding:14px;border-radius:12px;background:#1b2b40;display:flex;justify-content:space-between;align-items:center;gap:10px}
.robot-state strong{font-size:14px}.robot-state span{font-size:12px;color:var(--muted)}
.tablewrap{width:100%;overflow-x:auto;border-radius:10px;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;min-width:560px}th,td{text-align:left;padding:11px 9px;border-bottom:1px solid var(--line);font-size:13px;white-space:nowrap}
th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.35px;background:#111e30;position:sticky;top:0}
.table-hint{font-size:11px;color:var(--muted);margin:8px 0 0}
.section-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.small-button{padding:8px 10px;min-height:36px;font-size:12px}
footer{padding:6px 2px 18px}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.robot-grid{grid-template-columns:1fr}.card{border-radius:14px}header{align-items:flex-start}.pill{font-size:11px}}
@media(max-width:380px){main{padding:8px}.grid{gap:7px}.value{font-size:18px}.label{font-size:10px}button,select{font-size:14px;padding:11px}.card{padding:11px}}
</style>
</head>
<body><main>
<header>
  <div><h1>◈ Bolsa IA</h1><small>Simulador de investimentos da B3</small></div>
  <span class="pill">● MODO SIMULADO</span>
</header>
<div class="notice"><b>Somente dinheiro fictício.</b> O modo real está bloqueado: este site não envia ordens à bolsa. Preços podem atrasar ou ficar indisponíveis; o robô não garante lucro.</div>

<section class="grid" aria-label="Resumo financeiro">
  <div class="card"><div class="label">SALDO DISPONÍVEL</div><div class="value" id="saldo">R$ 10.000,00</div></div>
  <div class="card"><div class="label">PATRIMÔNIO TOTAL</div><div class="value" id="patrimonio">R$ 10.000,00</div></div>
  <div class="card"><div class="label">LUCRO / PREJUÍZO</div><div class="value" id="lucro">R$ 0,00</div></div>
  <div class="card"><div class="label">RESULTADO REALIZADO HOJE</div><div class="value" id="dia">R$ 0,00</div></div>
</section>

<section class="card">
  <div class="section-heading"><h2>Gráfico do mercado</h2><span class="pill" id="cotacaoStatus">Aguardando cotação</span></div>
  <form class="controls" id="config">
    <select id="ticker" aria-label="Escolher ação">
      <option value="PETR4.SA">PETR4 — Petrobras</option><option value="VALE3.SA">VALE3 — Vale</option>
      <option value="ITUB4.SA">ITUB4 — Itaú</option><option value="BBDC4.SA">BBDC4 — Bradesco</option>
      <option value="BBAS3.SA">BBAS3 — Banco do Brasil</option><option value="ABEV3.SA">ABEV3 — Ambev</option>
      <option value="WEGE3.SA">WEGE3 — WEG</option><option value="MGLU3.SA">MGLU3 — Magazine Luiza</option>
    </select>
    <button type="submit">Atualizar gráfico</button><button type="button" class="secondary" id="telaCheia">Tela cheia</button>
  </form>
  <p>Preço mais recente: <b id="preco">Consultando…</b></p>
  <div id="chartbox"><canvas id="grafico"></canvas></div>
  <p class="muted" id="atualizacao" aria-live="polite">Aguardando dados do mercado…</p>
</section>

<section class="card">
  <div class="section-heading"><h2>Controles do robô</h2><span class="pill">Estratégia de teste</span></div>
  <p class="muted">Regra educativa: compara a média dos últimos 5 preços com a média dos últimos 20. É uma regra simples, não uma recomendação de investimento.</p>
  <div class="robot-grid">
    <div>
      <p class="label">ESTADO ATUAL</p>
      <div class="robot-state"><strong id="robo">Verificando…</strong><span id="ultimaAvaliacao">Sem avaliação ainda</span></div>
    </div>
    <div>
      <p class="label">LIMITES DA SIMULAÇÃO</p>
      <div class="robot-state"><strong>Até 10%</strong><span>do patrimônio por compra</span></div>
    </div>
  </div>
  <form class="controls" method="post" action="/controle" style="margin-top:14px">
    <button name="modo" value="ligar" type="submit">Ativar robô</button>
    <button class="stop" name="modo" value="parar" type="submit">Pausar robô</button>
    <button class="secondary" name="modo" value="zerar" type="submit" onclick="return confirm('Reiniciar o saldo fictício e apagar o histórico desta sessão?')">Reiniciar simulação</button>
  </form>
  <p class="muted">O robô só avalia sinais quando o painel consulta o servidor. Se o serviço estiver suspenso ou não houver cotações, ele não opera. Mantenha pausado enquanto estiver aprendendo.</p>
</section>

<section class="card">
  <div class="section-heading"><h2>Carteira simulada</h2><span class="pill" id="totalPosicoes">0 posições</span></div>
  <div class="tablewrap"><table><thead><tr><th>Ação</th><th>Qtd.</th><th>Preço médio</th><th>Valor atual</th><th>Resultado</th></tr></thead>
  <tbody id="carteira"><tr><td colspan="5">Carregando…</td></tr></tbody></table></div>
  <p class="table-hint">No celular, deslize a tabela para os lados para ver todas as colunas.</p>
</section>

<section class="card">
  <div class="section-heading"><h2>Operações recentes</h2><button type="button" class="secondary small-button" id="atualizarTudo">Atualizar dados</button></div>
  <div class="tablewrap"><table><thead><tr><th>Data/hora</th><th>Operação</th><th>Ação</th><th>Qtd.</th><th>Preço</th></tr></thead>
  <tbody id="operacoes"><tr><td colspan="5">Nenhuma operação ainda</td></tr></tbody></table></div>
  <p class="table-hint">No celular, deslize a tabela para os lados para ver todas as colunas.</p>
</section>
<footer class="muted">Bolsa IA é um projeto educativo. Dados externos podem atrasar, faltar ou conter erros. Não é uma corretora e não garante retorno.</footer>
</main>
<script>
let chart=null,busy=false;
const money=n=>Number(n||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function drawChart(labels,values){
 if(typeof Chart==='undefined'){document.getElementById('atualizacao').textContent='A biblioteca do gráfico não carregou. Verifique a conexão e recarregue a página.';return;}
 const canvas=document.getElementById('grafico');
 if(!chart){chart=new Chart(canvas,{type:'line',data:{labels,datasets:[{label:'Preço (R$)',data:values,borderColor:'#4ade80',backgroundColor:'rgba(74,222,128,.12)',fill:true,tension:.2,pointRadius:0,borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{labels:{color:'#e8effa'}}},scales:{x:{ticks:{color:'#9aabc2',maxTicksLimit:7,maxRotation:35},grid:{color:'#263850'}},y:{ticks:{color:'#9aabc2'},grid:{color:'#263850'}}}}});}
 else{chart.data.labels=labels;chart.data.datasets[0].data=values;chart.update('none');}
}
async function refresh(){
 if(busy)return;busy=true;
 try{
  const symbol=document.getElementById('ticker').value;
  const response=await fetch('/api/tick?ticker='+encodeURIComponent(symbol),{cache:'no-store'});
  const data=await response.json();
  if(!response.ok)throw new Error(data.erro||'Não foi possível consultar os dados.');
  document.getElementById('cotacaoStatus').textContent=data.dados_ok?'Cotação recebida':'Sem cotação';
  document.getElementById('preco').textContent=data.preco==null?'Indisponível':money(data.preco);
  document.getElementById('atualizacao').textContent=data.atualizado?'Última consulta: '+data.atualizado:'Sem atualização';
  document.getElementById('saldo').textContent=money(data.saldo);
  document.getElementById('patrimonio').textContent=money(data.patrimonio);
  document.getElementById('lucro').textContent=money(data.lucro_total);
  document.getElementById('dia').textContent=money(data.lucro_dia);
  document.getElementById('robo').textContent=data.automatico?'ATIVO — SIMULAÇÃO':'PAUSADO';
  document.getElementById('robo').className=data.automatico?'green':'';
  document.getElementById('ultimaAvaliacao').textContent=data.dados_ok?'Dados verificados agora':'Aguardando dados';
  document.getElementById('lucro').className='value '+(data.lucro_total>=0?'green':'red');
  document.getElementById('dia').className='value '+(data.lucro_dia>=0?'green':'red');
  document.getElementById('totalPosicoes').textContent=data.carteira.length+' posição(ões)';
  document.getElementById('carteira').innerHTML=data.carteira.length?data.carteira.map(p=>`<tr><td>${safe(p.ticker)}</td><td>${p.qtd}</td><td>${money(p.medio)}</td><td>${money(p.valor)}</td><td class="${p.lucro>=0?'green':'red'}">${money(p.lucro)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma ação em carteira</td></tr>';
  document.getElementById('operacoes').innerHTML=data.operacoes.length?data.operacoes.map(o=>`<tr><td>${safe(o.hora)}</td><td>${safe(o.tipo)}</td><td>${safe(o.ticker)}</td><td>${o.qtd}</td><td>${money(o.preco)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma operação registrada</td></tr>';
  drawChart(data.labels||[],data.valores||[]);
 }catch(error){document.getElementById('cotacaoStatus').textContent='Falha na consulta';document.getElementById('atualizacao').textContent=error.message+' Tente novamente em alguns segundos.';}
 finally{busy=false;}
}
document.getElementById('config').addEventListener('submit',e=>{e.preventDefault();refresh();});
document.getElementById('atualizarTudo').addEventListener('click',refresh);
document.getElementById('telaCheia').addEventListener('click',async()=>{
 const box=document.getElementById('chartbox');
 try{if(!document.fullscreenElement)await box.requestFullscreen();else await document.exitFullscreen();}
 catch(e){document.getElementById('atualizacao').textContent='Tela cheia não disponível neste navegador.';}
});
refresh();setInterval(refresh,60000);
</script>
</body></html>
"""

def new_state():
    return {"saldo": INITIAL_BALANCE, "carteira": {}, "operacoes": [], "automatico": False, "ultima_sinal": {}, "realizado_dia": {}}

def get_state():
    if "conta" not in session or not isinstance(session.get("conta"), dict):
        session["conta"] = new_state()
    return session["conta"]

def fetch_prices(ticker):
    try:
        frame = yf.Ticker(ticker).history(period="5d", interval="5m", auto_adjust=False)
        if frame.empty or "Close" not in frame:
            frame = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
    except Exception:
        try:
            frame = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
        except Exception:
            return []
    if frame.empty or "Close" not in frame:
        return []
    result = []
    for moment, price in frame["Close"].dropna().tail(100).items():
        try:
            label = moment.strftime("%d/%m %H:%M") if hasattr(moment, "strftime") else str(moment)
            result.append((label, round(float(price), 2)))
        except (TypeError, ValueError):
            continue
    return result

def record_trade(account, kind, ticker, quantity, price, realized=0.0):
    now = datetime.now()
    account["operacoes"].insert(0, {"hora": now.strftime("%d/%m %H:%M:%S"), "data": now.strftime("%d/%m"), "tipo": kind, "ticker": ticker, "qtd": int(quantity), "preco": round(float(price), 2), "resultado": round(float(realized), 2)})
    account["operacoes"] = account["operacoes"][:50]
    if kind == "VENDA":
        day = now.strftime("%d/%m")
        account.setdefault("realizado_dia", {})
        account["realizado_dia"][day] = round(float(account["realizado_dia"].get(day, 0.0)) + float(realized), 2)

def run_strategy(account, ticker, prices):
    if not account.get("automatico") or len(prices) < 20:
        return
    short_avg = sum(prices[-5:]) / 5
    long_avg = sum(prices[-20:]) / 20
    signal = "comprar" if short_avg > long_avg else "vender"
    previous = account.setdefault("ultima_sinal", {}).get(ticker)
    if previous == signal:
        return
    account["ultima_sinal"][ticker] = signal
    portfolio = account.setdefault("carteira", {})
    position = portfolio.get(ticker, {"qtd": 0, "medio": 0.0})
    quantity = int(position.get("qtd", 0))
    cash = float(account.get("saldo", INITIAL_BALANCE))
    price = float(prices[-1])
    if price <= 0:
        return
    if signal == "comprar" and quantity == 0:
        current_assets = sum(int(p.get("qtd", 0)) * float(p.get("medio", 0)) for p in portfolio.values())
        equity = cash + current_assets
        buy_quantity = int(min(cash, equity * 0.10) // price)
        if buy_quantity > 0:
            cost = buy_quantity * price
            account["saldo"] = round(cash - cost, 2)
            portfolio[ticker] = {"qtd": buy_quantity, "medio": price}
            record_trade(account, "COMPRA", ticker, buy_quantity, price)
    elif signal == "vender" and quantity > 0:
        proceeds = quantity * price
        realized = quantity * (price - float(position.get("medio", price)))
        account["saldo"] = round(cash + proceeds, 2)
        record_trade(account, "VENDA", ticker, quantity, price, realized)
        portfolio.pop(ticker, None)

@app.route("/")
def home():
    get_state()
    return render_template_string(HTML)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "modo": "simulado", "ordens_reais": False})

@app.route("/controle", methods=["POST"])
def control():
    account = get_state()
    mode = request.form.get("modo", "")
    if mode == "ligar":
        account["automatico"] = True
    elif mode == "parar":
        account["automatico"] = False
    elif mode == "zerar":
        account.clear()
        account.update(new_state())
    session["conta"] = account
    session.modified = True
    return redirect(url_for("home"))

@app.route("/api/tick")
def tick():
    ticker = request.args.get("ticker", "PETR4.SA").upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{4,7}\.SA", ticker) or ticker not in ALLOWED_TICKERS:
        return jsonify({"erro": "Código de ação inválido. Escolha uma ação da lista."}), 400
    account = get_state()
    try:
        points = fetch_prices(ticker)
    except Exception:
        points = []
    prices = [p[1] for p in points]
    latest = prices[-1] if prices else None
    if latest is not None:
        run_strategy(account, ticker, prices)
    holdings, assets_value = [], 0.0
    for symbol, position in account.get("carteira", {}).items():
        try:
            quotes = points if symbol == ticker else fetch_prices(symbol)
            current = quotes[-1][1] if quotes else float(position.get("medio", 0.0))
        except Exception:
            current = float(position.get("medio", 0.0))
        qty, average = int(position.get("qtd", 0)), float(position.get("medio", 0.0))
        value, profit = qty * current, qty * (current - average)
        assets_value += value
        holdings.append({"ticker": symbol, "qtd": qty, "medio": round(average, 2), "valor": round(value, 2), "lucro": round(profit, 2)})
    cash = float(account.get("saldo", INITIAL_BALANCE))
    equity = cash + assets_value
    today = datetime.now().strftime("%d/%m")
    session["conta"] = account
    session.modified = True
    return jsonify({
        "dados_ok": latest is not None, "preco": latest, "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "saldo": round(cash, 2), "patrimonio": round(equity, 2), "lucro_total": round(equity - INITIAL_BALANCE, 2),
        "lucro_dia": round(float(account.get("realizado_dia", {}).get(today, 0.0)), 2),
        "automatico": bool(account.get("automatico")), "carteira": holdings, "operacoes": account.get("operacoes", [])[:20],
        "labels": [p[0] for p in points], "valores": prices
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
 
