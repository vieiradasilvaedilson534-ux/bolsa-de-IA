import os, re
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bolsa-ia-simulacao-trocar-no-render')
INITIAL_BALANCE = 10000.0
TICKERS = {'PETR4.SA','VALE3.SA','ITUB4.SA','BBDC4.SA','BBAS3.SA','ABEV3.SA','WEGE3.SA','MGLU3.SA'}

HTML = r'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bolsa IA — Simulador</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>
*{box-sizing:border-box}body{margin:0;background:#07111f;color:#e8effa;font:15px Arial,sans-serif}main{max-width:1100px;margin:auto;padding:14px}header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}h1{color:#4ade80;margin:0}h2{font-size:19px}.muted,small{color:#9aabc2;line-height:1.5}.pill,.status{display:inline-block;padding:9px 12px;border-radius:9px;background:#1b2b40}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:16px 0}.card{background:#111e30;border:1px solid #263850;border-radius:14px;padding:15px;margin-bottom:14px;min-width:0}.label{font-size:12px;color:#9aabc2}.value{font-size:clamp(20px,4vw,26px);font-weight:bold;margin-top:8px;overflow-wrap:anywhere}.green{color:#4ade80}.red{color:#fb7185}button,select{border:0;border-radius:8px;padding:12px;font-size:15px;max-width:100%}select{background:#e9f0fb;color:#101827}button{background:#4ade80;color:#062b17;font-weight:bold}button.secondary{background:#35465f;color:white}button.stop{background:#fb7185;color:#450a0a}form{display:flex;flex-wrap:wrap;gap:8px;align-items:center}#chartbox{height:320px;position:relative;margin-top:12px}.notice{padding:12px;border:1px solid #73551d;background:#302515;color:#fbd38d;border-radius:9px;line-height:1.5}.tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:500px}th,td{text-align:left;padding:10px 6px;border-bottom:1px solid #263850;font-size:13px}@media(max-width:500px){main{padding:9px}#chartbox{height:260px}.card{padding:12px}}
</style></head><body><main>
<header><div><h1>◈ Bolsa IA</h1><small>Simulador educativo da B3</small></div><span class="pill">MODO SIMULADO · DINHEIRO FICTÍCIO</span></header>
<div class="notice" style="margin-top:14px"><b>Modo real bloqueado.</b> Este site não envia ordens à bolsa nem movimenta dinheiro real. Cotações podem atrasar ou ficar indisponíveis. O robô não garante lucro.</div>
<div class="grid"><div class="card"><div class="label">SALDO DISPONÍVEL</div><div class="value" id="saldo">R$ 10.000,00</div></div><div class="card"><div class="label">PATRIMÔNIO</div><div class="value" id="patrimonio">R$ 10.000,00</div></div><div class="card"><div class="label">LUCRO / PREJUÍZO TOTAL</div><div class="value" id="lucro">R$ 0,00</div></div><div class="card"><div class="label">RESULTADO REALIZADO HOJE</div><div class="value" id="dia">R$ 0,00</div></div></div>
<section class="card"><h2>Gráfico do mercado</h2><form id="config"><select id="ticker"><option value="PETR4.SA">PETR4 — Petrobras</option><option value="VALE3.SA">VALE3 — Vale</option><option value="ITUB4.SA">ITUB4 — Itaú</option><option value="BBDC4.SA">BBDC4 — Bradesco</option><option value="BBAS3.SA">BBAS3 — Banco do Brasil</option><option value="ABEV3.SA">ABEV3 — Ambev</option><option value="WEGE3.SA">WEGE3 — WEG</option><option value="MGLU3.SA">MGLU3 — Magazine Luiza</option></select><button>Atualizar gráfico</button><button type="button" class="secondary" id="fullscreen">Tela cheia</button></form><p>Preço: <b id="preco">Consultando…</b></p><div id="chartbox"><canvas id="grafico"></canvas></div><p class="muted" id="info">Buscando cotações…</p></section>
<section class="card"><h2>Robô de negociação simulado</h2><p class="muted">Regra educativa: compara médias dos últimos 5 e 20 preços. É simples e não é recomendação de investimento. Compra limitada a 10% do patrimônio fictício, sem alavancagem.</p><form method="post" action="/controle"><button name="modo" value="ligar">Ativar robô</button><button class="stop" name="modo" value="parar">Pausar robô</button><button class="secondary" name="modo" value="zerar" onclick="return confirm('Reiniciar saldo e histórico fictícios?')">Reiniciar simulação</button></form><p class="status">Estado: <b id="robo">Verificando…</b></p><p class="muted">O robô só avalia sinais quando o painel consulta o servidor; não funciona continuamente se o serviço estiver suspenso.</p></section>
<section class="card"><h2>Carteira simulada</h2><div class="tablewrap"><table><thead><tr><th>Ação</th><th>Qtd.</th><th>Preço médio</th><th>Valor atual</th><th>Resultado</th></tr></thead><tbody id="carteira"><tr><td colspan="5">Carregando…</td></tr></tbody></table></div></section>
<section class="card"><h2>Operações recentes</h2><div class="tablewrap"><table><thead><tr><th>Horário</th><th>Operação</th><th>Ação</th><th>Qtd.</th><th>Preço</th></tr></thead><tbody id="ops"><tr><td colspan="5">Nenhuma operação</td></tr></tbody></table></div></section><p class="muted">Bolsa IA é apenas para aprendizagem. Preços podem estar atrasados ou indisponíveis. Nenhum dinheiro real é usado.</p></main>
<script>
let chart=null,busy=false;const money=n=>Number(n||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function draw(labels,values){if(typeof Chart==='undefined'){document.getElementById('info').textContent='Biblioteca do gráfico não carregou. Verifique a internet e recarregue.';return}if(!chart){chart=new Chart(document.getElementById('grafico'),{type:'line',data:{labels,datasets:[{label:'Preço (R$)',data:values,borderColor:'#4ade80',backgroundColor:'rgba(74,222,128,.12)',fill:true,tension:.2,pointRadius:0,borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{labels:{color:'#e8effa'}}},scales:{x:{ticks:{color:'#9aabc2',maxTicksLimit:7},grid:{color:'#263850'}},y:{ticks:{color:'#9aabc2'},grid:{color:'#263850'}}}}})}else{chart.data.labels=labels;chart.data.datasets[0].data=values;chart.update('none')}}
async function refresh(){if(busy)return;busy=true;try{let symbol=document.getElementById('ticker').value;let res=await fetch('/api/tick?ticker='+encodeURIComponent(symbol),{cache:'no-store'});let d=await res.json();if(!res.ok)throw Error(d.erro||'Erro na consulta');document.getElementById('status');document.querySelector('header .pill').textContent=d.dados_ok?'MODO SIMULADO · DADOS RECEBIDOS':'MODO SIMULADO · SEM COTAÇÃO';document.getElementById('preco').textContent=d.preco==null?'Indisponível':money(d.preco);document.getElementById('info').textContent=d.atualizado?'Consulta: '+d.atualizado+(d.dados_ok?'':' — provedor sem dados no momento'):'Sem atualização';for(let k of ['saldo','patrimonio','lucro','dia'])document.getElementById(k).textContent=money(d[{saldo:'saldo',patrimonio:'patrimonio',lucro:'lucro_total',dia:'lucro_dia'}[k]]);document.getElementById('lucro').className='value '+(d.lucro_total>=0?'green':'red');document.getElementById('dia').className='value '+(d.lucro_dia>=0?'green':'red');document.getElementById('robo').textContent=d.automatico?'ATIVO':'PAUSADO';document.getElementById('carteira').innerHTML=d.carteira.length?d.carteira.map(p=>`<tr><td>${esc(p.ticker)}</td><td>${p.qtd}</td><td>${money(p.medio)}</td><td>${money(p.valor)}</td><td class="${p.lucro>=0?'green':'red'}">${money(p.lucro)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma ação em carteira</td></tr>';document.getElementById('ops').innerHTML=d.operacoes.length?d.operacoes.map(o=>`<tr><td>${esc(o.hora)}</td><td>${esc(o.tipo)}</td><td>${esc(o.ticker)}</td><td>${o.qtd}</td><td>${money(o.preco)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma operação registrada</td></tr>';draw(d.labels||[],d.valores||[])}catch(e){document.getElementById('info').textContent=e.message+' — tente novamente em alguns segundos.';document.querySelector('header .pill').textContent='MODO SIMULADO · ERRO DE CONSULTA'}finally{busy=false}}
document.getElementById('config').addEventListener('submit',e=>{e.preventDefault();refresh()});document.getElementById('fullscreen').addEventListener('click',async()=>{try{let b=document.getElementById('chartbox');if(!document.fullscreenElement)await b.requestFullscreen();else await document.exitFullscreen()}catch(e){document.getElementById('info').textContent='Tela cheia não disponível neste navegador.'}});refresh();setInterval(refresh,60000);
</script></body></html>'''

def new_state():
    return {'saldo': INITIAL_BALANCE, 'carteira': {}, 'operacoes': [], 'automatico': False, 'ultima_sinal': {}, 'realizado_dia': {}}

def account():
    if not isinstance(session.get('conta'), dict): session['conta'] = new_state()
    return session['conta']

def prices_for(ticker):
    try:
        df = yf.Ticker(ticker).history(period='5d', interval='5m')
        if df.empty or 'Close' not in df: df = yf.Ticker(ticker).history(period='3mo', interval='1d')
    except Exception:
        df = yf.Ticker(ticker).history(period='3mo', interval='1d')
    if df.empty or 'Close' not in df: return []
    out=[]
    for time, price in df['Close'].dropna().tail(100).items():
        try: out.append((time.strftime('%d/%m %H:%M'), round(float(price),2)))
        except (ValueError, TypeError): pass
    return out

def record(a, kind, ticker, qty, price, result=0):
    now=datetime.now(); a['operacoes'].insert(0, {'hora':now.strftime('%d/%m %H:%M:%S'),'tipo':kind,'ticker':ticker,'qtd':int(qty),'preco':round(float(price),2),'resultado':round(float(result),2)})
    a['operacoes']=a['operacoes'][:50]
    if kind=='VENDA':
        day=now.strftime('%d/%m'); a.setdefault('realizado_dia',{}); a['realizado_dia'][day]=round(a['realizado_dia'].get(day,0)+result,2)

def strategy(a,ticker,values):
    if not a.get('automatico') or len(values)<20: return
    signal='comprar' if sum(values[-5:])/5 > sum(values[-20:])/20 else 'vender'
    if a.setdefault('ultima_sinal',{}).get(ticker)==signal: return
    a['ultima_sinal'][ticker]=signal; book=a['carteira']; pos=book.get(ticker,{'qtd':0,'medio':0.0}); qty=int(pos['qtd']); price=float(values[-1]); cash=float(a['saldo'])
    if price<=0:return
    if signal=='comprar' and qty==0:
        equity=cash+sum(int(p['qtd'])*float(p['medio']) for p in book.values()); buy_qty=int(min(cash,equity*.10)//price)
        if buy_qty>0:
            a['saldo']=round(cash-buy_qty*price,2); book[ticker]={'qtd':buy_qty,'medio':price}; record(a,'COMPRA',ticker,buy_qty,price)
    elif signal=='vender' and qty>0:
        result=qty*(price-float(pos['medio'])); a['saldo']=round(cash+qty*price,2); record(a,'VENDA',ticker,qty,price,result); book.pop(ticker,None)

@app.route('/')
def home(): account(); return render_template_string(HTML)

@app.route('/health')
def health(): return jsonify({'status':'ok','modo':'simulado','ordens_reais':False})

@app.route('/controle',methods=['POST'])
def control():
    a=account(); mode=request.form.get('modo')
    if mode=='ligar':a['automatico']=True
    elif mode=='parar':a['automatico']=False
    elif mode=='zerar':a.clear();a.update(new_state())
    session['conta']=a;session.modified=True;return redirect(url_for('home'))

@app.route('/api/tick')
def tick():
    ticker=request.args.get('ticker','PETR4.SA').upper().strip()
    if not re.fullmatch(r'[A-Z0-9]{4,7}\.SA',ticker) or ticker not in TICKERS:return jsonify({'erro':'Código de ação inválido. Escolha uma ação da lista.'}),400
    a=account()
    try: points=prices_for(ticker)
    except Exception: points=[]
    values=[p[1] for p in points]; latest=values[-1] if values else None
    if latest is not None:strategy(a,ticker,values)
    holdings=[]; assets=0.0
    for symbol,pos in a['carteira'].items():
        try: quotes=points if symbol==ticker else prices_for(symbol); current=quotes[-1][1] if quotes else float(pos['medio'])
        except Exception:current=float(pos['medio'])
        qty=int(pos['qtd']); average=float(pos['medio']); value=qty*current; profit=qty*(current-average); assets+=value
        holdings.append({'ticker':symbol,'qtd':qty,'medio':round(average,2),'valor':round(value,2),'lucro':round(profit,2)})
    cash=float(a['saldo']); equity=cash+assets; today=datetime.now().strftime('%d/%m')
    session['conta']=a;session.modified=True
    return jsonify({'dados_ok':latest is not None,'preco':latest,'atualizado':datetime.now().strftime('%d/%m/%Y %H:%M:%S'),'saldo':round(cash,2),'patrimonio':round(equity,2),'lucro_total':round(equity-INITIAL_BALANCE,2),'lucro_dia':round(float(a.get('realizado_dia',{}).get(today,0)),2),'automatico':bool(a['automatico']),'carteira':holdings,'operacoes':a['operacoes'][:20],'labels':[p[0] for p in points],'valores':values})

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
  
