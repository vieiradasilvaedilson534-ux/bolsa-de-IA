import os
import re
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import yfinance as yf
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-no-render")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
INITIAL_BALANCE = 10000.0
ALLOCATION_PER_ASSET_BRL = 5.0
B3_TICKERS = {"PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "WEGE3.SA", "MGLU3.SA"}
US_STOCKS = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA"}
TRADEABLE_STOCKS = US_STOCKS | B3_TICKERS
MARKETS = US_STOCKS | {
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "WEGE3.SA", "MGLU3.SA",
    "^N225", "^HSI", "000001.SS", "399001.SZ", "^KS11", "^TWII", "^STI", "^AXJO", "^NSEI", "^BSESN",
    "^GSPC", "^IXIC", "^DJI", "^RUT", "^BVSP", "^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^AORD", "^IBEX", "FTSEMIB.MI",
    "BRL=X", "EURBRL=X", "EURUSD=X", "JPYBRL=X", "CNYBRL=X", "GBPBRL=X", "AUDUSD=X", "USDJPY=X", "USDCNY=X",
    "GC=F", "SI=F", "CL=F", "BZ=F", "BTC-USD", "ETH-USD"
}
HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Bolsa IA — Painel Global v2</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{color-scheme:dark;--bg:#07111f;--panel:#111e30;--line:#263850;--text:#e8effa;--muted:#9aabc2;--green:#4ade80;--red:#fb7185;--blue:#93c5fd;--gold:#fbbf24}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,Arial,sans-serif}
main{width:min(1150px,100%);margin:auto;padding:clamp(9px,3vw,20px)}header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:4px 0 14px}
h1{margin:0;color:var(--green);font-size:clamp(24px,5vw,31px)}h2{font-size:19px;margin:0 0 14px}h3{font-size:15px;margin:0 0 8px}.muted,small{color:var(--muted)}.muted{line-height:1.55;font-size:13px}
.pill{display:inline-flex;align-items:center;padding:7px 10px;border-radius:999px;background:#1b2c42;color:var(--blue);font-size:12px;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:clamp(12px,2.5vw,18px);margin-bottom:14px;min-width:0}
.label{font-size:11px;color:var(--muted);letter-spacing:.4px;font-weight:700}.value{font-size:clamp(19px,2.5vw,27px);font-weight:800;margin-top:8px;overflow-wrap:anywhere}
.green{color:var(--green)}.red{color:var(--red)}.gold{color:var(--gold)}
form.controls{display:flex;flex-wrap:wrap;align-items:center;gap:9px}
input,select,button{border:0;border-radius:10px;padding:12px;font-size:15px;max-width:100%;min-height:44px}
input,select{background:#e9f0fb;color:#101827}select{flex:1 1 190px;min-width:0}input{width:100%}
button{background:var(--green);color:#062b17;font-weight:750;cursor:pointer;touch-action:manipulation}
button.secondary{background:#35465f;color:#fff}button.stop{background:var(--red);color:#450a0a}button:disabled{opacity:.5;cursor:not-allowed}
.notice{border:1px solid #6b4c1c;background:#302515;color:#fbd38d;border-radius:12px;padding:12px 14px;line-height:1.5;font-size:13px;margin:4px 0 14px}
.statgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.stat{padding:12px;border-radius:12px;background:#0c1828;border:1px solid #203149;min-width:0}.stat .value{font-size:clamp(17px,2vw,22px)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.robot-state{padding:12px;border-radius:12px;background:#1b2b40;display:flex;justify-content:space-between;align-items:center;gap:10px}
.tablewrap{width:100%;overflow-x:auto;border-radius:10px;-webkit-overflow-scrolling:touch}table{width:100%;border-collapse:collapse;min-width:550px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);font-size:13px;white-space:nowrap}th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.3px}
.hint{font-size:11px;color:var(--muted);margin-top:7px}.sectionhead{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.bar{height:9px;border-radius:9px;background:#263850;overflow:hidden}.bar>span{display:block;height:100%;width:0;background:var(--green);transition:width .2s}
.checks{display:flex;flex-wrap:wrap;gap:12px}.checks label{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px}.checks input{width:auto;min-height:0}
footer{padding:5px 2px 18px}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.two{grid-template-columns:1fr}.statgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:380px){main{padding:8px}.grid{gap:7px}.value{font-size:18px}.label{font-size:10px}.card{padding:11px}button,select{font-size:14px;padding:11px}}
</style>
</head>
<body><main>
<header><div><h1>◈ Bolsa IA</h1><small>Painel global v2 — mercados do mundo</small></div><span class="pill">● MODO SIMULADO</span></header>
<div class="notice"><b>Ambiente educativo:</b> só usa dinheiro fictício e não envia ordens reais. Indicadores e testes usam dados históricos disponíveis; resultados passados não garantem resultados futuros.</div>
<section class="grid" aria-label="Resumo financeiro">
<div class="card"><div class="label">SALDO DISPONÍVEL</div><div class="value" id="saldo">R$ 10.000,00</div></div>
<div class="card"><div class="label">PATRIMÔNIO TOTAL</div><div class="value" id="patrimonio">R$ 10.000,00</div></div>
<div class="card"><div class="label">LUCRO / PREJUÍZO</div><div class="value" id="lucro">R$ 0,00</div></div>
<div class="card"><div class="label">RESULTADO REALIZADO HOJE</div><div class="value" id="dia">R$ 0,00</div></div>
</section>
<section class="card">
<div class="sectionhead"><h2>Mercados globais e indicadores</h2><span class="pill" id="cotacaoStatus">Aguardando cotação</span></div>
<form class="controls" id="config">
<select id="ticker" aria-label="Escolher mercado ou ativo">
<optgroup label="Estados Unidos — ações (robô simulado)"><option value="AAPL">AAPL — Apple</option><option value="MSFT">MSFT — Microsoft</option><option value="NVDA">NVDA — NVIDIA</option><option value="AMZN">AMZN — Amazon</option><option value="GOOGL">GOOGL — Alphabet</option><option value="TSLA">TSLA — Tesla</option></optgroup>
<optgroup label="Brasil — B3 (negociação simulada)"><option value="PETR4.SA">PETR4 — Petrobras</option><option value="VALE3.SA">VALE3 — Vale</option><option value="ITUB4.SA">ITUB4 — Itaú</option><option value="BBDC4.SA">BBDC4 — Bradesco</option><option value="BBAS3.SA">BBAS3 — Banco do Brasil</option><option value="ABEV3.SA">ABEV3 — Ambev</option><option value="WEGE3.SA">WEGE3 — WEG</option><option value="MGLU3.SA">MGLU3 — Magazine Luiza</option></optgroup>
<optgroup label="Ásia — índices"><option value="^N225">Japão — Nikkei 225</option><option value="^HSI">Hong Kong — Hang Seng</option><option value="000001.SS">China — Shanghai Composite</option><option value="399001.SZ">China — Shenzhen Component</option><option value="^KS11">Coreia do Sul — KOSPI</option><option value="^TWII">Taiwan — Taiwan Weighted</option><option value="^STI">Singapura — Straits Times</option><option value="^NSEI">Índia — Nifty 50</option><option value="^BSESN">Índia — Sensex</option><option value="^AXJO">Austrália — ASX 200</option></optgroup>
<optgroup label="Américas — índices"><option value="^GSPC">EUA — S&P 500</option><option value="^IXIC">EUA — Nasdaq Composite</option><option value="^DJI">EUA — Dow Jones</option><option value="^RUT">EUA — Russell 2000</option><option value="^BVSP">Brasil — Ibovespa</option></optgroup>
<optgroup label="Europa — índices"><option value="^FTSE">Reino Unido — FTSE 100</option><option value="^GDAXI">Alemanha — DAX</option><option value="^FCHI">França — CAC 40</option><option value="^STOXX50E">Zona do euro — Euro Stoxx 50</option><option value="^IBEX">Espanha — IBEX 35</option><option value="FTSEMIB.MI">Itália — FTSE MIB</option></optgroup>
<optgroup label="Moedas e câmbio"><option value="BRL=X">USD/BRL — dólar em reais</option><option value="EURBRL=X">EUR/BRL — euro em reais</option><option value="EURUSD=X">EUR/USD — euro em dólar</option><option value="JPYBRL=X">JPY/BRL — iene em reais</option><option value="CNYBRL=X">CNY/BRL — yuan em reais</option><option value="GBPBRL=X">GBP/BRL — libra em reais</option><option value="AUDUSD=X">AUD/USD — dólar australiano/dólar</option><option value="USDJPY=X">USD/JPY — dólar/iene</option><option value="USDCNY=X">USD/CNY — dólar/yuan</option></optgroup>
<optgroup label="Commodities e cripto (apenas gráfico) "><option value="GC=F">Ouro</option><option value="SI=F">Prata</option><option value="CL=F">Petróleo WTI</option><option value="BZ=F">Petróleo Brent</option><option value="BTC-USD">Bitcoin</option><option value="ETH-USD">Ethereum</option></optgroup>
</select><input id="customTicker" type="text" maxlength="24" placeholder="Ou digite um símbolo (ex.: MXRF11.SA, BOVA11.SA, BTC-USD)" aria-label="Digitar símbolo do ativo" style="flex:1 1 240px"><button type="submit">Atualizar</button><button type="button" class="secondary" id="telaCheia">Tela cheia</button>
</form>
<div class="checks" style="margin-top:12px">
<label><input type="checkbox" id="showSma" checked> Média móvel 5</label>
<label><input type="checkbox" id="showLma" checked> Média móvel 20</label>
</div>
<p>Cotação mais recente (moeda/unidade original): <b id="preco">Consultando…</b></p>
<div id="chartbox"><canvas id="grafico"></canvas></div>
<div class="statgrid" style="margin-top:12px">
<div class="stat"><div class="label">VARIAÇÃO NO PERÍODO</div><div class="value" id="variacao">—</div></div>
<div class="stat"><div class="label">MÉDIA MÓVEL 5</div><div class="value" id="media5">—</div></div>
<div class="stat"><div class="label">MÉDIA MÓVEL 20</div><div class="value" id="media20">—</div></div>
<div class="stat"><div class="label">RSI (14)</div><div class="value" id="rsi">—</div></div>
<div class="stat"><div class="label">MÁXIMA DO PERÍODO</div><div class="value" id="maxima">—</div></div>
<div class="stat"><div class="label">MÍNIMA DO PERÍODO</div><div class="value" id="minima">—</div></div>
</div>
<p class="muted" id="atualizacao" aria-live="polite">Aguardando dados…</p>
</section>
<section class="card">
<div class="sectionhead"><h2>Teste histórico da estratégia</h2><span class="pill">Sem dinheiro real</span></div>
<p class="muted">Simula uma estratégia de cruzamento das médias móveis de 5 e 20 períodos usando os preços históricos disponíveis. O teste inclui uma taxa simulada por operação, mas não prevê o futuro e não reproduz perfeitamente custos, impostos ou execução real.</p>
<form class="controls" id="backtestForm">
<select id="periodo" aria-label="Período histórico"><option value="6mo">Últimos 6 meses</option><option value="1y" selected>Último ano</option><option value="2y">Últimos 2 anos</option><option value="5y">Últimos 5 anos</option></select>
<select id="taxa" aria-label="Custo simulado"><option value="0">Custo: 0%</option><option value="0.001" selected>Custo: 0,1% por operação</option><option value="0.002">Custo: 0,2% por operação</option></select>
<button type="submit" id="runBacktest">Executar teste</button>
</form>
<p class="muted" id="backtestStatus" aria-live="polite">Escolha o período e toque em Executar teste.</p>
<div class="statgrid">
<div class="stat"><div class="label">RETORNO DA ESTRATÉGIA</div><div class="value" id="btRetorno">—</div></div>
<div class="stat"><div class="label">COMPRAR E MANTER</div><div class="value" id="btHold">—</div></div>
<div class="stat"><div class="label">MÁXIMA QUEDA (DRAWDOWN)</div><div class="value" id="btDrawdown">—</div></div>
<div class="stat"><div class="label">OPERAÇÕES FECHADAS</div><div class="value" id="btTrades">—</div></div>
<div class="stat"><div class="label">TAXA DE ACERTO</div><div class="value" id="btWin">—</div></div>
<div class="stat"><div class="label">SALDO FINAL DE TESTE</div><div class="value" id="btFinal">—</div></div>
</div>
<p class="hint">O teste é histórico e hipotético. Uma estratégia pode ter bom resultado no passado e perder dinheiro no futuro.</p>
</section>
<section class="card">
<div class="sectionhead"><h2>Controles do robô</h2><span class="pill">Carteira fictícia</span></div>
<p class="muted">Modo multiactivo: o robô verifica <b>todas as 14 ações listadas neste aplicativo</b>, sem depender da ação selecionada no gráfico. Quando houver sinal de compra, tenta alocar até R$ 5 fictícios naquele ativo. Ações americanas são convertidas para reais pela cotação USD/BRL. Índices, moedas, commodities e cripto ficam disponíveis para consulta, mas não são ações e não entram neste robô.</p>
<div class="statgrid" style="margin:12px 0"><div class="stat"><div class="label">AÇÕES DOS EUA</div><div class="value">6</div><small>AAPL, MSFT, NVDA, AMZN, GOOGL, TSLA</small></div><div class="stat"><div class="label">AÇÕES DA B3</div><div class="value">8</div><small>PETR4, VALE3, ITUB4, BBDC4, BBAS3, ABEV3, WEGE3, MGLU3</small></div></div>
<div class="notice"><b>Limite do modo multiactivo:</b> ele analisa ações cadastradas (EUA + B3), não literalmente todos os instrumentos do mundo. A carteira é simulada; não há envio de ordens reais.</div>
<div class="two">
<div><div class="label">ESTADO</div><div class="robot-state"><b id="robo">Verificando…</b><span id="robotNote">—</span></div></div>
<div><div class="label">PROTEÇÃO</div><div class="robot-state"><b>Dinheiro fictício</b><span>Ordens reais bloqueadas</span></div></div>
</div>
<form class="controls" method="post" action="/controle" style="margin-top:14px">
<button name="modo" value="ligar" type="submit">Ativar robô — 14 ações (até R$ 5 cada)</button><button class="stop" name="modo" value="parar" type="submit">Pausar robô</button><button class="secondary" name="modo" value="zerar" type="submit" onclick="return confirm('Reiniciar saldo fictício e apagar o histórico desta sessão?')">Reiniciar simulação</button>
</form>
<p class="muted">Se os dados estiverem indisponíveis ou o serviço estiver suspenso, o robô não avalia sinais. Para aprendizado, mantenha-o pausado até entender os resultados.</p>
</section>
<section class="card">
<div class="sectionhead"><h2>Carteira simulada</h2><span class="pill" id="totalPosicoes">0 posições</span></div>
<div class="tablewrap"><table><thead><tr><th>Ação</th><th>Qtd.</th><th>Preço médio</th><th>Valor atual</th><th>Resultado</th></tr></thead><tbody id="carteira"><tr><td colspan="5">Carregando…</td></tr></tbody></table></div><p class="hint">No celular, deslize para os lados para ver todas as colunas.</p>
</section>
<section class="card">
<div class="sectionhead"><h2>Operações recentes</h2><button type="button" class="secondary" id="atualizarTudo">Atualizar dados</button></div>
<div class="tablewrap"><table><thead><tr><th>Data/hora</th><th>Operação</th><th>Ação</th><th>Qtd.</th><th>Preço</th></tr></thead><tbody id="operacoes"><tr><td colspan="5">Nenhuma operação ainda</td></tr></tbody></table></div><p class="hint">No celular, deslize para os lados para ver todas as colunas.</p>
</section>
<footer class="muted">Bolsa IA é um laboratório educativo, não uma corretora. Índices, moedas, commodities e cripto são apenas para consulta; cotações podem atrasar, usar unidades diferentes ou faltar. Nenhuma estatística ou indicador garante retorno.</footer>
</main>
<script>
let chart=null,busy=false,lastPrices=[],lastLabels=[];
const money=n=>Number(n||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const quote=n=>Number(n||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:4});
const isUSStock=symbol=>['AAPL','MSFT','NVDA','AMZN','GOOGL','TSLA'].includes(String(symbol));
const pct=n=>(n>=0?'+':'')+Number(n||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function sma(arr,period){return arr.map((_,i)=>i+1<period?null:arr.slice(i-period+1,i+1).reduce((a,b)=>a+b,0)/period);}
function calcRsi(values,period=14){
 if(values.length<period+1)return null;let gain=0,loss=0;
 for(let i=values.length-period;i<values.length;i++){const d=values[i]-values[i-1];if(d>0)gain+=d;else loss-=d;}
 if(loss===0)return gain===0?50:100;const rs=(gain/period)/(loss/period);return 100-(100/(1+rs));
}
function drawChart(labels,values){
 if(typeof Chart==='undefined'){document.getElementById('atualizacao').textContent='Biblioteca do gráfico não carregou. Verifique a conexão.';return;}
 const sma5=sma(values,5),sma20=sma(values,20),datasets=[{label:'Preço (R$)',data:values,borderColor:'#4ade80',backgroundColor:'rgba(74,222,128,.08)',fill:true,tension:.18,pointRadius:0,borderWidth:2}];
 if(document.getElementById('showSma').checked)datasets.push({label:'Média 5',data:sma5,borderColor:'#60a5fa',pointRadius:0,borderWidth:1.5,spanGaps:false});
 if(document.getElementById('showLma').checked)datasets.push({label:'Média 20',data:sma20,borderColor:'#fbbf24',pointRadius:0,borderWidth:1.5,spanGaps:false});
 if(!chart){chart=new Chart(document.getElementById('grafico'),{type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{labels:{color:'#e8effa'}}},scales:{x:{ticks:{color:'#9aabc2',maxTicksLimit:7,maxRotation:35},grid:{color:'#263850'}},y:{ticks:{color:'#9aabc2'},grid:{color:'#263850'}}}}});}
 else{chart.data.labels=labels;chart.data.datasets=datasets;chart.update('none');}
}
function updateIndicators(values){
 const put=(id,value,cls='')=>{const el=document.getElementById(id);el.textContent=value;el.className='value '+cls;};
 if(!values.length){['variacao','media5','media20','rsi','maxima','minima'].forEach(id=>put(id,'—'));return;}
 const first=values[0],last=values[values.length-1],change=first?((last/first)-1)*100:0;
 const m5=values.length>=5?values.slice(-5).reduce((a,b)=>a+b,0)/5:null;
 const m20=values.length>=20?values.slice(-20).reduce((a,b)=>a+b,0)/20:null;
 const rsi=calcRsi(values);
 put('variacao',pct(change),change>=0?'green':'red');put('media5',m5===null?'Dados insuficientes':quote(m5));put('media20',m20===null?'Dados insuficientes':quote(m20));
 put('rsi',rsi===null?'Dados insuficientes':rsi.toLocaleString('pt-BR',{maximumFractionDigits:1})+(rsi>=70?' — alto':rsi<=30?' — baixo':''),rsi!==null&&rsi>=70?'red':rsi!==null&&rsi<=30?'green':'');
 put('maxima',quote(Math.max(...values)));put('minima',quote(Math.min(...values)));
}
async function refresh(){
 if(busy)return;busy=true;
 try{
  const symbol=(document.getElementById('customTicker').value.trim()||document.getElementById('ticker').value).toUpperCase();
  const response=await fetch('/api/tick?ticker='+encodeURIComponent(symbol),{cache:'no-store'});
  let data;try{data=await response.json();}catch(parseError){throw new Error('O servidor retornou uma resposta inválida. Atualize a página e tente novamente.');}if(!response.ok)throw new Error(data.erro||'Falha ao consultar os dados.');
  lastPrices=data.valores||[];lastLabels=data.labels||[];
  document.getElementById('cotacaoStatus').textContent=data.dados_ok?'Cotação recebida':'Sem cotação';
  document.getElementById('preco').textContent=data.preco==null?'Indisponível':quote(data.preco);
  document.getElementById('atualizacao').textContent=data.atualizado?'Última consulta: '+data.atualizado:'Sem atualização';
  document.getElementById('saldo').textContent=money(data.saldo);document.getElementById('patrimonio').textContent=money(data.patrimonio);
  document.getElementById('lucro').textContent=money(data.lucro_total);document.getElementById('dia').textContent=money(data.lucro_dia);
  document.getElementById('lucro').className='value '+(data.lucro_total>=0?'green':'red');document.getElementById('dia').className='value '+(data.lucro_dia>=0?'green':'red');
  document.getElementById('robo').textContent=data.automatico?'ATIVO — SIMULAÇÃO':'PAUSADO';document.getElementById('robo').className=data.automatico?'green':'';
  document.getElementById('robotNote').textContent=data.automatico?'Analisa ações cadastradas dos EUA + B3; R$ 5 por entrada simulada':(data.dados_ok?'Robô pausado; gráfico atualizado':'Aguardando cotação');
  document.getElementById('totalPosicoes').textContent=data.carteira.length+' posição(ões)';
  document.getElementById('carteira').innerHTML=data.carteira.length?data.carteira.map(p=>`<tr><td>${safe(p.ticker)}</td><td>${p.qtd}</td><td>${money(p.medio)}</td><td>${money(p.valor)}</td><td class="${p.lucro>=0?'green':'red'}">${money(p.lucro)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma ação em carteira</td></tr>';
  document.getElementById('operacoes').innerHTML=data.operacoes.length?data.operacoes.map(o=>`<tr><td>${safe(o.hora)}</td><td>${safe(o.tipo)}</td><td>${safe(o.ticker)}</td><td>${o.qtd}</td><td>${money(o.preco)}</td></tr>`).join(''):'<tr><td colspan="5">Nenhuma operação registrada</td></tr>';
  drawChart(data.labels||[],lastPrices);updateIndicators(lastPrices);
 }catch(error){document.getElementById('cotacaoStatus').textContent='Falhaao consultar';document.getElementById('atualizacao').textContent=error.message||'Não foi possível carregar os dados.';document.getElementById('preco').textContent='Indisponível';
}finally{busy=false;}
}
document.getElementById('config').addEventListener('submit',e=>{e.preventDefault();refresh();});
document.getElementById('ticker').addEventListener('change',()=>{document.getElementById('customTicker').value='';refresh();});
document.getElementById('customTicker').addEventListener('change',refresh);
document.getElementById('showSma').addEventListener('change',()=>drawChart(lastLabels,lastPrices));
document.getElementById('showLma').addEventListener('change',()=>drawChart(lastLabels,lastPrices));
document.getElementById('atualizarTudo').addEventListener('click',refresh);
document.getElementById('telaCheia').addEventListener('click',async()=>{
try{
const el=document.getElementById('chartbox');
if(!document.fullscreenElement){await el.requestFullscreen();}
else{await document.exitFullscreen();}
}catch(e){document.getElementById('atualizacao').textContent='Tela cheia não disponível neste navegador.';}
});
document.getElementById('backtestForm').addEventListener('submit',async e=>{
e.preventDefault();
const btn=document.getElementById('runBacktest');
const status=document.getElementById('backtestStatus');
btn.disabled=true;status.textContent='Executando teste histórico…';
try{
const symbol=(document.getElementById('customTicker').value.trim()||document.getElementById('ticker').value).toUpperCase();
const periodo=document.getElementById('periodo').value;
const taxa=document.getElementById('taxa').value;
const r=await fetch('/api/backtest?ticker='+encodeURIComponent(symbol)+'&periodo='+encodeURIComponent(periodo)+'&taxa='+encodeURIComponent(taxa));
const d=await r.json();
if(!r.ok)throw new Error(d.erro||'Não foi possível executar o teste.');
document.getElementById('btRetorno').textContent=pct(d.retorno);
document.getElementById('btHold').textContent=pct(d.hold);
document.getElementById('btDrawdown').textContent=pct(d.drawdown);
document.getElementById('btTrades').textContent=d.operacoes;
document.getElementById('btWin').textContent=d.taxa_acerto.toLocaleString('pt-BR',{maximumFractionDigits:1})+'%';
document.getElementById('btFinal').textContent=money(d.saldo_final);
status.textContent='Teste concluído com '+d.pontos+' preços históricos. Resultado hipotético.';
}catch(err){status.textContent=err.message||'Erro no teste histórico.';}
finally{btn.disabled=false;}
});
refresh();
setInterval(refresh,60000);
</script>
</body>
</html>
"""
def novo_estado():
    return {
        "saldo": INITIAL_BALANCE,
        "carteira": {},
        "operacoes": [],
        "automatico": False,
        "multiactivo": True,
        "processados": {},
    }
def estado():
    if "estado_bolsa" not in session:
        session["estado_bolsa"] = novo_estado()
    return session["estado_bolsa"]
def ticker_valido(ticker):
    # Símbolos usuais do Yahoo Finance: ações, FIIs/ETFs, índices, câmbio, futuros e cripto.
    # Validação sintática apenas; a fonte de dados confirma se o símbolo existe.
    return bool(ticker and len(ticker) <= 24 and re.fullmatch(r"[A-Z0-9^=._-]+", ticker))

def buscar_historico(ticker, periodo="5d", intervalo="15m"):
    ticker = str(ticker or "").strip().upper()
    if not ticker_valido(ticker):
        raise ValueError("Símbolo inválido. Confira o código do ativo.")
    dados = yf.Ticker(ticker).history(period=periodo, interval=intervalo, auto_adjust=True)
    if dados is None or dados.empty or "Close" not in dados:
        return [], []
    dados = dados.dropna(subset=["Close"])
    valores = [round(float(x), 6) for x in dados["Close"].tolist()]
    datas = [x.strftime("%d/%m %H:%M") for x in dados.index]
    return datas[-len(valores):], valores
def calcular_rsi(valores, periodo=14):
    if len(valores) <= periodo:
        return None
    movimentos = [valores[i] - valores[i - 1] for i in range(len(valores) - periodo, len(valores))]
    ganhos = sum(max(x, 0) for x in movimentos) / periodo
    perdas = sum(max(-x, 0) for x in movimentos) / periodo
    if perdas == 0:
        return 100.0 if ganhos > 0 else 50.0
    rs = ganhos / perdas
    return 100 - (100 / (1 + rs))
def sinal_compra(valores, i=None):
    """Filtro conservador didático: cruzamento 5/20, acima da SMA50 e RSI 45–65."""
    if i is None:
        i = len(valores) - 1
    if i < 50:
        return False
    curta_antes = sum(valores[i - 5:i]) / 5
    longa_antes = sum(valores[i - 20:i]) / 20
    curta = sum(valores[i - 4:i + 1]) / 5
    longa = sum(valores[i - 19:i + 1]) / 20
    sma50 = sum(valores[i - 49:i + 1]) / 50
    rsi = calcular_rsi(valores[:i + 1])
    return curta_antes <= longa_antes and curta > longa and valores[i] > sma50 and rsi is not None and 45 <= rsi <= 65
def simular_robo(ticker, valores, estado_atual, preco_brl=None):
    """Executa somente operações fictícias, limitadas a R$ 5 por ativo."""
    if not estado_atual.get("automatico") or ticker not in TRADEABLE_STOCKS or len(valores) < 51:
        return
    carteira = estado_atual.setdefault("carteira", {})
    operacoes = estado_atual.setdefault("operacoes", [])
    posicao = carteira.get(ticker, {"qtd": 0.0, "custo": 0.0})
    qtd = float(posicao.get("qtd", 0))
    preco_local = float(valores[-1])
    # Ações dos EUA cotam em USD; convertemos para BRL para respeitar o limite de R$ 5.
    if ticker in US_STOCKS:
        if preco_brl is None or preco_brl <= 0:
            return
        preco = preco_local * float(preco_brl)
    else:
        preco = preco_local
    saldo = float(estado_atual.get("saldo", INITIAL_BALANCE))
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    curta = sum(valores[-5:]) / 5
    longa = sum(valores[-20:]) / 20
    if qtd <= 0 and sinal_compra(valores):
        investimento = min(ALLOCATION_PER_ASSET_BRL, saldo)
        quantidade = investimento / preco if preco > 0 else 0.0
        if quantidade > 0 and investimento >= 0.01:
            custo = quantidade * preco
            estado_atual["saldo"] = saldo - custo
            carteira[ticker] = {"qtd": quantidade, "custo": custo, "moeda": "BRL"}
            operacoes.insert(0, {"hora": agora, "tipo": "COMPRA SIMULADA R$ 5", "ticker": ticker, "qtd": round(quantidade, 8), "preco": preco})
    elif qtd > 0 and curta < longa:
        custo = float(posicao.get("custo", 0))
        recebido = qtd * preco
        estado_atual["saldo"] = saldo + recebido
        operacoes.insert(0, {"hora": agora, "tipo": "VENDA SIMULADA", "ticker": ticker, "qtd": round(qtd, 8), "preco": preco})
        carteira.pop(ticker, None)
    estado_atual["operacoes"] = operacoes[:100]

def processar_todos_ativos(estado_atual):
    """Avalia cada ação elegível quando o painel é atualizado; nunca envia ordens reais."""
    if not estado_atual.get("automatico"):
        return
    try:
        fx_labels, fx_values = buscar_historico("BRL=X", "5d", "1d")
        usdbrl = fx_values[-1] if fx_values else None
    except Exception:
        usdbrl = None
    for simbolo in sorted(TRADEABLE_STOCKS):
        try:
            _, diarios = buscar_historico(simbolo, "1y", "1d")
            conversao = usdbrl if simbolo in US_STOCKS else None
            simular_robo(simbolo, diarios, estado_atual, conversao)
        except Exception:
            app.logger.warning("Sem dados para avaliar %s", simbolo)

@app.route("/")
def inicio():
    return render_template_string(HTML)
@app.route("/controle", methods=["POST"])
def controle():
    atual = estado()
    modo = request.form.get("modo", "")
    if modo == "ligar":
        atual["automatico"] = True
    elif modo == "parar":
        atual["automatico"] = False
    elif modo == "zerar":
        atual = novo_estado()
    session["estado_bolsa"] = atual
    session.modified = True
    return redirect(url_for("inicio"))
@app.route("/api/tick")
def api_tick():
    ticker = request.args.get("ticker", "AAPL")
    if not ticker_valido(ticker):
        return jsonify({"erro": "Símbolo inválido. Use o código do ativo, por exemplo AAPL, PETR4.SA ou BTC-USD."}), 400
    atual = estado()
    try:
        labels, valores = buscar_historico(ticker, "5d", "15m")
        if not valores:
            return jsonify({"erro": "Não há cotações disponíveis para este ativo agora."}), 503
        # O robô avalia todas as ações cadastradas, não apenas o símbolo do gráfico.
        processar_todos_ativos(atual)
        session["estado_bolsa"] = atual
        session.modified = True
        preco = valores[-1]
        carteira_resumo = []
        total_acoes = 0.0
        for simbolo, posicao in atual.get("carteira", {}).items():
            try:
                _, cotacoes = buscar_historico(simbolo, "5d", "1d")
                preco_atual = cotacoes[-1] if cotacoes else float(posicao.get("custo", 0)) / max(1, float(posicao.get("qtd", 1)))
                if simbolo in US_STOCKS:
                    _, fx = buscar_historico("BRL=X", "5d", "1d")
                    if fx:
                        preco_atual *= fx[-1]
            except Exception:
                preco_atual = float(posicao.get("custo", 0)) / max(1e-8, float(posicao.get("qtd", 1)))
            quantidade = float(posicao.get("qtd", 0))
            custo = float(posicao.get("custo", 0))
            valor = quantidade * preco_atual
            total_acoes += valor
            carteira_resumo.append({"ticker": simbolo, "qtd": quantidade, "medio": custo / quantidade if quantidade else 0, "valor": valor, "lucro": valor - custo})
        saldo = float(atual.get("saldo", INITIAL_BALANCE))
        patrimonio = saldo + total_acoes
        return jsonify({"dados_ok": True, "labels": labels[-100:], "valores": valores[-100:], "preco": preco, "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "saldo": saldo, "patrimonio": patrimonio, "lucro_total": patrimonio - INITIAL_BALANCE, "lucro_dia": 0.0, "automatico": bool(atual.get("automatico")), "multiactivo": True, "universo_robo": sorted(TRADEABLE_STOCKS), "total_acoes_monitoradas": len(TRADEABLE_STOCKS), "carteira": carteira_resumo, "operacoes": atual.get("operacoes", [])[:30]})
    except Exception:
        app.logger.exception("Falha ao consultar cotações")
        return jsonify({"erro": "Falha ao consultar dados do mercado. Tente novamente mais tarde."}), 503
@app.route("/api/backtest")
def api_backtest():
    ticker = request.args.get("ticker", "AAPL")
    periodo = request.args.get("periodo", "1y")
    taxa_texto = request.args.get("taxa", "0.001")
    if not ticker_valido(ticker):
        return jsonify({"erro": "Símbolo inválido. Use o código do ativo, por exemplo AAPL, PETR4.SA ou BTC-USD."}), 400
    if periodo not in {"6mo", "1y", "2y", "5y"}:
        return jsonify({"erro": "Período inválido."}), 400
    try:
        taxa = float(taxa_texto)
        if not 0 <= taxa <= 0.02:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"erro": "Taxa inválida."}), 400
    try:
        _, valores = buscar_historico(ticker, periodo, "1d")
        if len(valores) < 60:
            return jsonify({"erro": "Dados históricos insuficientes; tente outro período ou ação."}), 503
        saldo = INITIAL_BALANCE
        quantidade = 0.0
        preco_compra = 0.0
        custo_compra = 0.0
        patrimonio_maximo = INITIAL_BALANCE
        drawdown_maximo = 0.0
        operacoes = 0
        vencedoras = 0
        for i in range(50, len(valores)):
            preco = valores[i]
            if quantidade == 0 and ticker in US_STOCKS and sinal_compra(valores[:i + 1]):
                quantidade = saldo / (preco * (1 + taxa))
                preco_compra = preco
                custo_compra = quantidade * preco * (1 + taxa)
                saldo -= custo_compra
            elif quantidade > 0:
                curta = sum(valores[i - 4:i + 1]) / 5
                longa = sum(valores[i - 19:i + 1]) / 20
                if curta < longa:
                    resultado = quantidade * preco * (1 - taxa) - custo_compra
                    if resultado > 0:
                        vencedoras += 1
                    saldo += quantidade * preco * (1 - taxa)
                    quantidade = 0.0
                    operacoes += 1
            patrimonio = saldo + quantidade * preco
            patrimonio_maximo = max(patrimonio_maximo, patrimonio)
            if patrimonio_maximo > 0:
                drawdown_maximo = max(drawdown_maximo, (patrimonio_maximo - patrimonio) / patrimonio_maximo)
        saldo_final = saldo + quantidade * valores[-1]
        retorno = (saldo_final / INITIAL_BALANCE - 1) * 100
        hold = (valores[-1] / valores[0] - 1) * 100
        taxa_acerto = (vencedoras / operacoes * 100) if operacoes else 0.0
        return jsonify({"retorno": retorno, "hold": hold, "drawdown": drawdown_maximo * 100, "operacoes": operacoes, "vencedoras": vencedoras, "taxa_acerto": taxa_acerto, "saldo_final": saldo_final, "pontos": len(valores)})
    except Exception:
        app.logger.exception("Falha no backtest")
        return jsonify({"erro": "Não foi possível executar o teste histórico agora."}), 503
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
