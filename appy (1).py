import os
import time
import threading
import random
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-no-render")

INITIAL_BALANCE = 10000.0
ASSETS = {
    "BTC-USD": ("Bitcoin", "CRYPTO"),
    "ETH-USD": ("Ethereum", "CRYPTO"),
    "PETR4.SA": ("Petrobras", "B3"),
    "VALE3.SA": ("Vale", "B3"),
    "ITUB4.SA": ("Itaú", "B3"),
    "BBDC4.SA": ("Bradesco", "B3"),
    "BBAS3.SA": ("Banco do Brasil", "B3"),
    "ABEV3.SA": ("Ambev", "B3"),
    "WEGE3.SA": ("WEG", "B3"),
    "MGLU3.SA": ("Magazine Luiza", "B3"),
    "AAPL": ("Apple", "EUA"),
    "MSFT": ("Microsoft", "EUA"),
    "NVDA": ("NVIDIA", "EUA"),
    "AMZN": ("Amazon", "EUA"),
    "GOOGL": ("Alphabet", "EUA"),
    "TSLA": ("Tesla", "EUA"),
}
LOCK = threading.RLock()
STATE = {
    "balance": INITIAL_BALANCE,
    "positions": [],
    "history": [],
    "robot_on": False,
    "last_robot_check": 0,
    "prices": {},
    "price_mode": "demo",
    "last_update": None,
}

HTML = r"""
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bolsa IA — Terminal de Simulação</title>
<script src="https://unpkg.com/lightweight-charts@4.2.2/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{color-scheme:dark;--bg:#080b10;--panel:#111720;--panel2:#0c1118;--line:#26303d;--txt:#e6edf6;--muted:#91a0b4;--green:#23d9a1;--red:#ff5268;--blue:#579bff;--gold:#ffc857}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:13px/1.4 system-ui,Arial,sans-serif}button,input,select{font:inherit;border-radius:7px;border:1px solid var(--line);padding:10px;background:#151d28;color:var(--txt);min-height:38px}button{cursor:pointer;font-weight:700}button:hover{filter:brightness(1.15)}.buy{background:#123e36;color:var(--green);border-color:#1d6c5a}.sell{background:#481f2a;color:#ff8493;border-color:#7c3040}.primary{background:var(--green);color:#03241a;border:0}.wrap{max-width:1500px;margin:auto;padding:12px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid var(--line);padding:8px 0 14px;flex-wrap:wrap}.brand{font-size:23px;font-weight:900;letter-spacing:1px;color:var(--green)}.sub{color:var(--muted);font-size:11px}.badge{border:1px solid #1d6c5a;background:#102c28;color:var(--green);border-radius:30px;padding:7px 10px;font-size:11px;font-weight:800}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:12px 0}.panel,.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;min-width:0}.stat{padding:12px}.label{font-size:10px;color:var(--muted);letter-spacing:.7px;text-transform:uppercase}.big{font-size:clamp(17px,2vw,24px);font-weight:850;margin-top:5px;overflow-wrap:anywhere}.green{color:var(--green)}.red{color:var(--red)}.blue{color:var(--blue)}.muted{color:var(--muted)}.layout{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(240px,1fr) minmax(230px,.85fr);gap:10px;align-items:start}.panel{padding:12px;margin-bottom:10px}.panel h2{font-size:13px;text-transform:uppercase;letter-spacing:.7px;margin:0 0 10px;color:#dbe6f5}.charthead{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}.price{font-size:22px;color:var(--blue);font-weight:850}.chartbox{height:340px;width:100%}#chart{height:100%;width:100%}.mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}.mini{background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:9px}.bookrow{display:grid;grid-template-columns:1fr 1fr;gap:8px}.bookside{min-width:0}.bookside h3{font-size:10px;color:var(--muted);margin:4px 0 8px}.bookline{display:flex;justify-content:space-between;gap:4px;padding:4px 3px;border-bottom:1px solid #202936;font-size:10px}.bookline span:last-child{color:var(--muted)}.centerprice{text-align:center;padding:9px;color:var(--green);font-size:16px;font-weight:900}.row{display:flex;gap:8px;align-items:center}.row>*{min-width:0;flex:1}.stack{display:grid;gap:8px}.stack label{display:grid;gap:4px;color:var(--muted);font-size:11px}.stack input,.stack select{width:100%}.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.wide{width:100%}.tablewrap{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;min-width:530px;font-size:11px}td,th{text-align:left;padding:9px 7px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--muted);font-size:10px;text-transform:uppercase}.bottomgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.notice{padding:10px;border:1px solid #6a5125;background:#2b2417;color:#f8d995;border-radius:8px;font-size:11px;margin:10px 0}.status{display:flex;justify-content:space-between;gap:8px;align-items:center;background:var(--panel2);padding:9px;border-radius:7px}.footer{color:var(--muted);font-size:10px;padding:10px 2px 20px}
@media(max-width:1050px){.layout{grid-template-columns:minmax(0,1.5fr) minmax(240px,1fr)}.tradecol{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:10px}.tradecol .panel{margin:0}}
@media(max-width:650px){.wrap{padding:8px}.stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.layout{grid-template-columns:1fr}.tradecol{grid-column:auto;display:block}.tradecol .panel{margin-bottom:10px}.chartbox{height:300px}.bottomgrid{grid-template-columns:1fr}.brand{font-size:20px}.big{font-size:18px}.panel{padding:10px}}
</style></head><body><div class="wrap">
<header class="top"><div><div class="brand">◈ BOLSA IA</div><div class="sub">TERMINAL GLOBAL • SIMULADOR DE TRADING</div></div><span class="badge">● DINHEIRO FICTÍCIO</span></header>
<div class="notice"><b>Modo educativo:</b> nenhuma ordem real é enviada. O modo demonstração usa preços artificiais para demonstrar movimentos; as cotações de referência podem atrasar. Uma taxa de acerto de 95% não é garantida.</div>
<section class="stats">
<div class="stat"><div class="label">Saldo disponível</div><div class="big" id="balance">R$ 10.000,00</div></div>
<div class="stat"><div class="label">Patrimônio estimado</div><div class="big" id="equity">R$ 10.000,00</div></div>
<div class="stat"><div class="label">Lucro / prejuízo total</div><div class="big" id="totalpl">R$ 0,00</div></div>
<div class="stat"><div class="label">Taxa de acerto encerradas</div><div class="big blue" id="winrate">—</div></div>
</section>
<div class="layout">
<section class="panel">
<div class="charthead"><div><h2 id="assetTitle">BTC-USD · Bitcoin</h2><div class="price" id="currentPrice">Carregando…</div><div class="sub" id="priceNote">Inicializando dados</div></div><div class="stack" style="min-width:130px"><label>Ativo<select id="asset"></select></label><label>Fonte de preço<select id="mode"><option value="demo">Simulação dinâmica</option><option value="reference">Cotação de referência</option></select></label></div></div>
<div class="chartbox"><div id="chart"></div></div>
<div class="mini-grid"><div class="mini"><div class="label">Variação da tela</div><div class="big" id="change">—</div></div><div class="mini"><div class="label">Posições abertas</div><div class="big" id="openCount">0</div></div><div class="mini"><div class="label">Resultado em aberto</div><div class="big" id="unrealized">R$ 0,00</div></div><div class="mini"><div class="label">Atualização</div><div class="big" style="font-size:13px" id="updated">—</div></div></div>
</section>
<section class="panel"><h2>Livro de ofertas</h2><div class="sub">Demonstração visual — não representa ordens reais</div><div class="bookrow"><div class="bookside"><h3>COMPRA · BID</h3><div id="bids"></div></div><div class="bookside"><h3>VENDA · ASK</h3><div id="asks"></div></div></div><div class="centerprice" id="bookPrice">—</div><div class="sub">Ofertas artificiais para fins educativos.</div></section>
<div class="tradecol">
<section class="panel"><h2>Negociação simulada</h2><form id="tradeForm" class="stack"><label>Direção<select id="side"><option value="buy">Comprar / Long</option><option value="sell">Vender / Short simulado</option></select></label><label>Valor da posição (R$)<input id="amount" type="number" min="10" max="1000" step="5" value="100" required></label><label>Duração<select id="duration"><option value="30">30 segundos</option><option value="60" selected>1 minuto</option><option value="300">5 minutos</option><option value="900">15 minutos</option></select></label><label>Stop-loss (R$)<input id="stop" type="number" min="0" step="1" value="10"></label><label>Meta de lucro (R$)<input id="target" type="number" min="0" step="1" value="10"></label><button class="primary wide" type="submit">Abrir posição simulada</button></form><div class="sub" style="margin-top:8px">Venda a descoberto é apenas uma hipótese matemática do simulador.</div></section>
<section class="panel"><h2>Robô automático</h2><div class="status"><b id="robotStatus">PAUSADO</b><span class="sub" id="robotMsg">Aguardando</span></div><div class="row" style="margin-top:8px"><button class="buy" id="startRobot">Iniciar</button><button class="sell" id="stopRobot">Pausar</button></div><p class="sub">Estratégia didática: cruzamento de médias 5/20 em preços simulados. Sem garantia de rentabilidade.</p></section>
</div>
</div>
<div class="bottomgrid">
<section class="panel"><h2>Posições abertas</h2><div class="tablewrap"><table><thead><tr><th>Ativo</th><th>Direção</th><th>Entrada</th><th>Preço atual</th><th>P/L</th><th>Tempo</th><th>Ação</th></tr></thead><tbody id="positions"><tr><td colspan="7">Nenhuma posição aberta.</td></tr></tbody></table></div></section>
<section class="panel"><h2>Histórico de operações</h2><div class="tablewrap"><table><thead><tr><th>Hora</th><th>Ativo</th><th>Direção</th><th>Entrada</th><th>Saída</th><th>Resultado líquido</th><th>Motivo</th></tr></thead><tbody id="history"><tr><td colspan="7">Nenhuma operação encerrada.</td></tr></tbody></table></div></section>
</div>
<div class="panel"><div class="charthead"><h2>Controles da conta simulada</h2><button class="sell" id="reset">Reiniciar simulação</button></div><div class="sub">Saldo inicial fictício de R$ 10.000. Cada posição tem limite de tamanho; a simulação não envia ordens para corretoras.</div></div>
<div class="footer">Bolsa IA é um laboratório educativo, não uma corretora. Preços simulados não representam o mercado. Cotações de referência podem atrasar. Não há garantia de lucro ou taxa de acerto.</div>
</div>
<script>
const ASSETS = __ASSETS__;
const money=n=>Number(n||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const fmt=(n,d=2)=>Number(n||0).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let chart,candleSeries,seriesData=[],currentAsset='BTC-USD',busy=false,lastTick=0;
function initChart(){
 const el=document.getElementById('chart');
 if(!window.LightweightCharts){el.innerHTML='<p class="sub">Biblioteca de gráfico indisponível. Verifique a conexão.</p>';return}
 chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:el.clientHeight,layout:{background:{color:'#111720'},textColor:'#91a0b4'},grid:{vertLines:{color:'#202936'},horzLines:{color:'#202936'}},rightPriceScale:{borderColor:'#26303d'},timeScale:{borderColor:'#26303d',timeVisible:true,secondsVisible:true},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}});
 candleSeries=chart.addCandlestickSeries({upColor:'#23d9a1',downColor:'#ff5268',borderUpColor:'#23d9a1',borderDownColor:'#ff5268',wickUpColor:'#23d9a1',wickDownColor:'#ff5268'});
 new ResizeObserver(()=>chart.applyOptions({width:el.clientWidth,height:el.clientHeight})).observe(el);
}
function fillAssets(){const s=document.getElementById('asset');s.innerHTML=Object.entries(ASSETS).map(([k,v])=>`<option value="${safe(k)}">${safe(k)} — ${safe(v[0])}</option>`).join('');s.value='BTC-USD'}
function book(price){
 const bids=document.getElementById('bids'),asks=document.getElementById('asks');let bh='',ah='';
 for(let i=0;i<7;i++){const b=price*(1-(i+1)*0.00035),a=price*(1+(i+1)*0.00035),q=(Math.random()*3+0.1).toFixed(4);bh+=`<div class="bookline"><span class="green">${fmt(b,price<10?5:2)}</span><span>${q}</span></div>`;ah+=`<div class="bookline"><span class="red">${fmt(a,price<10?5:2)}</span><span>${q}</span></div>`}
 bids.innerHTML=bh;asks.innerHTML=ah;document.getElementById('bookPrice').textContent=fmt(price,price<10?5:2);
}
function paintState(s){
 document.getElementById('balance').textContent=money(s.balance);
 document.getElementById('equity').textContent=money(s.equity);
 const p=document.getElementById('totalpl');p.textContent=money(s.total_pl);p.className='big '+(s.total_pl>=0?'green':'red');
 document.getElementById('winrate').textContent=s.win_rate===null?'—':fmt(s.win_rate)+'%';
 document.getElementById('openCount').textContent=s.positions.length;
 document.getElementById('unrealized').textContent=money(s.unrealized);
 document.getElementById('unrealized').className='big '+(s.unrealized>=0?'green':'red');
 document.getElementById('robotStatus').textContent=s.robot_on?'ATIVO':'PAUSADO';
 document.getElementById('robotMsg').textContent=s.robot_on?'Monitorando':'Aguardando';
 const pos=document.getElementById('positions');
 pos.innerHTML=s.positions.length?s.positions.map(x=>`<tr><td>${safe(x.symbol)}</td><td class="${x.side==='buy'?'green':'red'}">${x.side==='buy'?'COMPRA':'VENDA'}</td><td>${money(x.entry)}</td><td>${fmt(x.current,4)}</td><td class="${x.pl>=0?'green':'red'}">${money(x.pl)}</td><td>${x.remaining}s</td><td><button data-close="${x.id}" class="sell">Fechar</button></td></tr>`).join(''):'<tr><td colspan="7">Nenhuma posição aberta.</td></tr>';
 document.getElementById('history').innerHTML=s.history.length?s.history.slice().reverse().slice(0,30).map(x=>`<tr><td>${safe(x.time)}</td><td>${safe(x.symbol)}</td><td>${x.side==='buy'?'COMPRA':'VENDA'}</td><td>${fmt(x.entry,4)}</td><td>${fmt(x.exit,4)}</td><td class="${x.pl>=0?'green':'red'}">${money(x.pl)}</td><td>${safe(x.reason)}</td></tr>`).join(''):'<tr><td colspan="7">Nenhuma operação encerrada.</td></tr>';
 document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>closePosition(b.dataset.close));
}
async function tick(){
 if(busy)return;busy=true;
 try{
  const mode=document.getElementById('mode').value;
  const r=await fetch(`/api/tick?symbol=${encodeURIComponent(currentAsset)}&mode=${mode}`);
  const d=await r.json();if(!r.ok)throw new Error(d.error||'Erro de dados');
  document.getElementById('assetTitle').textContent=currentAsset+' · '+ASSETS[currentAsset][0];
  document.getElementById('currentPrice').textContent=fmt(d.price,d.price<10?5:2)+' '+(mode==='demo'?'SIM':'REF');
  document.getElementById('priceNote').textContent=mode==='demo'?'Preço artificial para demonstração':'Cotação de referência; pode atrasar';
  if(candleSeries&&d.candles.length){candleSeries.setData(d.candles);chart.timeScale().fitContent()}
  const start=d.candles.length?d.candles[0].close:d.price;
  const change=start?100*(d.price/start-1):0;const ce=document.getElementById('change');ce.textContent=(change>=0?'+':'')+fmt(change)+'%';ce.className='big '+(change>=0?'green':'red');
  book(d.price);document.getElementById('updated').textContent=new Date().toLocaleTimeString('pt-BR');
  paintState(d.account);
 }catch(e){document.getElementById('priceNote').textContent='Falha ao atualizar: '+e.message}
 finally{busy=false}
}
async function post(url,body={}){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw new Error(d.error||'Falha');return d}
document.getElementById('asset').onchange=e=>{currentAsset=e.target.value;tick()};
document.getElementById('mode').onchange=()=>tick();
document.getElementById('tradeForm').onsubmit=async e=>{e.preventDefault();try{await post('/api/open',{symbol:currentAsset,side:document.getElementById('side').value,amount:Number(document.getElementById('amount').value),duration:Number(document.getElementById('duration').value),stop:Number(document.getElementById('stop').value),target:Number(document.getElementById('target').value)});await tick()}catch(err){alert(err.message)}};
async function closePosition(id){try{await post('/api/close',{id});await tick()}catch(e){alert(e.message)}}
document.getElementById('startRobot').onclick=async()=>{try{await post('/api/robot',{on:true});await tick()}catch(e){alert(e.message)}};
document.getElementById('stopRobot').onclick=async()=>{try{await post('/api/robot',{on:false});await tick()}catch(e){alert(e.message)}};
document.getElementById('reset').onclick=async()=>{if(!confirm('Apagar o histórico e reiniciar os R$ 10.000 fictícios?'))return;try{await post('/api/reset');await tick()}catch(e){alert(e.message)}};
initChart();fillAssets();tick();setInterval(tick,1000);
</script></body></html>
"""

def _demo_price(symbol):
    # Stable-ish starting anchors, then a random walk for visual demonstration only.
    anchors = {"BTC-USD": 67000.0, "ETH-USD": 3300.0, "PETR4.SA": 36.0, "VALE3.SA": 62.0,
               "ITUB4.SA": 34.0, "BBDC4.SA": 15.0, "BBAS3.SA": 27.0, "ABEV3.SA": 12.0,
               "WEGE3.SA": 52.0, "MGLU3.SA": 8.0, "AAPL": 230.0, "MSFT": 510.0,
               "NVDA": 180.0, "AMZN": 225.0, "GOOGL": 250.0, "TSLA": 350.0}
    if symbol not in STATE["prices"]:
        STATE["prices"][symbol] = anchors.get(symbol, 100.0)
    old = STATE["prices"][symbol]
    change = random.gauss(0, 0.0007)
    new = max(old * 0.05, old * (1 + change))
    STATE["prices"][symbol] = new
    return new

def _reference_price(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="1d", interval="1m")
        if hist.empty:
            raise ValueError("A fonte não retornou cotações para este ativo.")
        price = float(hist["Close"].dropna().iloc[-1])
        if price <= 0:
            raise ValueError("Cotação inválida.")
        return price
    except Exception as exc:
        raise ValueError("Não foi possível obter cotação de referência. Tente novamente ou use a simulação.") from exc

def _candles(symbol, mode, current):
    # The demo candles are explicitly synthetic; reference mode uses historical OHLC.
    now = int(time.time())
    if mode == "reference":
        try:
            hist = yf.Ticker(symbol).history(period="1d", interval="5m").dropna()
            rows = []
            for idx, row in hist.tail(100).iterrows():
                ts = int(idx.timestamp())
                vals = [float(row[k]) for k in ("Open", "High", "Low", "Close")]
                if all(v > 0 for v in vals):
                    rows.append({"time": ts, "open": vals[0], "high": max(vals[1], *vals), "low": min(vals[2], *vals), "close": vals[3]})
            if len(rows) >= 2:
                return rows
        except Exception:
            pass
    # Generate a bounded synthetic path ending at current price.
    base = current
    out = []
    for i in range(80, -1, -1):
        ts = now - i * 60
        drift = random.gauss(0, 0.0015)
        op = max(base * 0.05, base * (1 + drift))
        cl = max(op * 0.05, op * (1 + random.gauss(0, 0.0015)))
        hi = max(op, cl) * (1 + random.random() * 0.0008)
        lo = min(op, cl) * (1 - random.random() * 0.0008)
        out.append({"time": ts, "open": op, "high": hi, "low": lo, "close": cl})
        base = cl
    out[-1]["close"] = current
    out[-1]["high"] = max(out[-1]["high"], current, out[-1]["open"])
    out[-1]["low"] = min(out[-1]["low"], current, out[-1]["open"])
    return out

def _mark_to_market(pos, price):
    direction = 1 if pos["side"] == "buy" else -1
    return (price - pos["entry"]) * pos["qty"] * direction

def _close_position(pos, price, reason):
    if pos not in STATE["positions"]:
        return
    gross = _mark_to_market(pos, price)
    fee = pos["amount"] * 0.001
    net = gross - fee
    STATE["balance"] += pos["amount"] + net
    STATE["history"].append({
        "id": pos["id"], "time": datetime.now().strftime("%d/%m %H:%M:%S"),
        "symbol": pos["symbol"], "side": pos["side"], "entry": pos["entry"],
        "exit": price, "pl": net, "reason": reason
    })
    STATE["positions"].remove(pos)

def _update_positions():
    now = time.time()
    for pos in list(STATE["positions"]):
        try:
            if STATE["price_mode"] == "demo":
                price = _demo_price(pos["symbol"])
            else:
                price = pos.get("last_price", pos["entry"])
            pos["last_price"] = price
            pl = _mark_to_market(pos, price) - pos["amount"] * 0.001
            elapsed = now - pos["opened_at"]
            reason = None
            if pos["stop"] > 0 and pl <= -pos["stop"]:
                reason = "Stop-loss"
            elif pos["target"] > 0 and pl >= pos["target"]:
                reason = "Meta de lucro"
            elif elapsed >= pos["duration"]:
                reason = "Tempo encerrado"
            if reason:
                _close_position(pos, price, reason)
        except Exception:
            continue

def _account():
    with LOCK:
        _update_positions()
        unrealized = 0.0
        position_rows = []
        equity = STATE["balance"]
        for pos in STATE["positions"]:
            price = pos.get("last_price", pos["entry"])
            pl = _mark_to_market(pos, price) - pos["amount"] * 0.001
            unrealized += pl
            equity += pos["amount"] + pl
            position_rows.append({
                "id": pos["id"], "symbol": pos["symbol"], "side": pos["side"],
                "entry": pos["entry"], "current": price, "pl": pl,
                "remaining": max(0, int(pos["duration"] - (time.time() - pos["opened_at"])))
            })
        closed = STATE["history"]
        wins = sum(1 for x in closed if x["pl"] > 0)
        win_rate = (100 * wins / len(closed)) if closed else None
        realized = sum(x["pl"] for x in closed)
        return {"balance": STATE["balance"], "equity": equity,
                "total_pl": realized + unrealized, "unrealized": unrealized,
                "positions": position_rows, "history": closed[-100:],
                "win_rate": win_rate, "robot_on": STATE["robot_on"]}

def _robot_step():
    with LOCK:
        if not STATE["robot_on"]:
            return
        now = time.time()
        if now - STATE["last_robot_check"] < 15:
            return
        STATE["last_robot_check"] = now
        # Educational demo strategy: use a short synthetic trend proxy, not a prediction.
        if len(STATE["positions"]) >= 3 or STATE["balance"] < 25:
            return
        symbol = "BTC-USD"
        price = _demo_price(symbol)
        # No claimed win rate; random choice prevents implying predictive capability.
        side = "buy" if random.random() >= 0.5 else "sell"
        amount = min(25.0, STATE["balance"], STATE["balance"] * 0.01)
        if amount < 10:
            return
        STATE["balance"] -= amount
        STATE["positions"].append({
            "id": str(int(time.time()*1000)), "symbol": symbol, "side": side,
            "entry": price, "last_price": price, "amount": amount,
            "qty": amount / price, "duration": 60, "stop": 5.0, "target": 5.0,
            "opened_at": now
        })

@app.get("/")
def index():
    assets = {k: list(v) for k, v in ASSETS.items()}
    return render_template_string(HTML.replace("__ASSETS__", json_dumps(assets)))

def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

@app.get("/api/tick")
def api_tick():
    symbol = request.args.get("symbol", "BTC-USD")
    mode = request.args.get("mode", "demo")
    if symbol not in ASSETS:
        return jsonify({"error": "Ativo não permitido."}), 400
    if mode not in ("demo", "reference"):
        return jsonify({"error": "Modo inválido."}), 400
    try:
        with LOCK:
            STATE["price_mode"] = mode
            price = _demo_price(symbol) if mode == "demo" else _reference_price(symbol)
            candles = _candles(symbol, mode, price)
            _robot_step()
            account = _account()
        return jsonify({"symbol": symbol, "price": price, "candles": candles,
                        "account": account, "server_time": datetime.now(timezone.utc).isoformat()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

@app.post("/api/open")
def api_open():
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol")
    side = data.get("side")
    try:
        amount = float(data.get("amount", 0))
        duration = int(data.get("duration", 60))
        stop = max(0.0, float(data.get("stop", 0)))
        target = max(0.0, float(data.get("target", 0)))
    except (TypeError, ValueError):
        return jsonify({"error": "Confira os valores informados."}), 400
    if symbol not in ASSETS or side not in ("buy", "sell"):
        return jsonify({"error": "Ativo ou direção inválidos."}), 400
    if not (10 <= amount <= 1000) or duration not in (30, 60, 300, 900):
        return jsonify({"error": "Valor ou duração fora dos limites permitidos."}), 400
    with LOCK:
        if amount > STATE["balance"]:
            return jsonify({"error": "Saldo fictício insuficiente."}), 400
        price = STATE["prices"].get(symbol)
        if not price:
            price = _demo_price(symbol)
        STATE["balance"] -= amount
        STATE["positions"].append({
            "id": str(int(time.time()*1000)) + str(random.randint(10,99)),
            "symbol": symbol, "side": side, "entry": price, "last_price": price,
            "amount": amount, "qty": amount / price, "duration": duration,
            "stop": stop, "target": target, "opened_at": time.time()
        })
        return jsonify({"ok": True, "account": _account()})

@app.post("/api/close")
def api_close():
    data = request.get_json(silent=True) or {}
    pos_id = str(data.get("id", ""))
    with LOCK:
        pos = next((p for p in STATE["positions"] if p["id"] == pos_id), None)
        if not pos:
            return jsonify({"error": "Posição não encontrada ou já encerrada."}), 404
        price = pos.get("last_price", pos["entry"])
        _close_position(pos, price, "Fechamento manual")
        return jsonify({"ok": True, "account": _account()})

@app.post("/api/robot")
def api_robot():
    data = request.get_json(silent=True) or {}
    with LOCK:
        STATE["robot_on"] = bool(data.get("on", False))
        if STATE["robot_on"]:
            STATE["last_robot_check"] = 0
        return jsonify({"ok": True, "robot_on": STATE["robot_on"]})

@app.post("/api/reset")
def api_reset():
    with LOCK:
        STATE["balance"] = INITIAL_BALANCE
        STATE["positions"] = []
        STATE["history"] = []
        STATE["robot_on"] = False
        STATE["prices"] = {}
        STATE["last_robot_check"] = 0
    return jsonify({"ok": True})

@app.get("/health")
def health():
    return jsonify({"ok": True, "app": "Bolsa IA", "mode": "simulation"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
