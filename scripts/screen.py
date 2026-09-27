"""Deterministic end-of-day Stocklist scoring. Python standard library only."""
import csv, json, math, os, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
WEIGHTS={'golden':20,'rsi':15,'macd':20,'obv':15,'bollinger':10,'stochastic':10,'market':10}

def sma(x,n):
    return [None if i<n-1 else sum(x[i-n+1:i+1])/n for i in range(len(x))]

def ema(x,n):
    out=[x[0]]
    for v in x[1:]: out.append(out[-1]+2/(n+1)*(v-out[-1]))
    return out

def rsi(x,n=14):
    out=[None]*len(x)
    gain=sum(max(x[i]-x[i-1],0) for i in range(1,n+1))/n
    loss=sum(max(x[i-1]-x[i],0) for i in range(1,n+1))/n
    for i in range(n,len(x)):
        if i>n:
            gain=(gain*(n-1)+max(x[i]-x[i-1],0))/n
            loss=(loss*(n-1)+max(x[i-1]-x[i],0))/n
        out[i]=100-100/(1+gain/loss) if loss else (100 if gain else 50)
    return out

def analyse(bars):
    if len(bars)<250: raise ValueError('At least 250 daily candles required')
    if len({b[0][:10] for b in bars})!=len(bars): raise ValueError('Duplicate dates')
    if bars!=sorted(bars,key=lambda b:b[0]): raise ValueError('Dates must be ascending')
    for b in bars:
        if len(b)<6 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in b[1:6]): raise ValueError('Invalid candle')
        if not (0<b[3]<=min(b[1],b[4])<=max(b[1],b[4])<=b[2] and b[5]>=0): raise ValueError('Invalid OHLCV')
    c=[b[4] for b in bars]; h=[b[2] for b in bars]; l=[b[3] for b in bars]
    s50=sma(c,50); s200=sma(c,200); rs=rsi(c)
    m=[a-b for a,b in zip(ema(c,12),ema(c,26))]; ms=ema(m,9)
    ob=[0]
    for i in range(1,len(c)): ob.append(ob[-1]+(1 if c[i]>c[i-1] else -1 if c[i]<c[i-1] else 0)*bars[i][5])
    mid=sma(c,20); low=[None if i<19 else mid[i]-2*math.sqrt(sum((v-mid[i])**2 for v in c[i-19:i+1])/20) for i in range(len(c))]
    k=[50 if i<13 or max(h[i-13:i+1])==min(l[i-13:i+1]) else 100*(c[i]-min(l[i-13:i+1]))/(max(h[i-13:i+1])-min(l[i-13:i+1])) for i in range(len(c))]; d=sma(k,3)
    cross=lambda a,b:any(a[i]>b[i] and a[i-1]<=b[i-1] for i in range(len(a)-5,len(a)))
    gc=cross(s50,s200); mc=cross(m,ms) and m[-1]>ms[-1]
    st=any(k[i]>d[i] and k[i-1]<=d[i-1] and min(k[i-1],d[i-1])<20 for i in range(len(k)-5,len(k))) and k[-1]>d[-1]
    rb=rs[-1]>rs[-2] and any(25<=v<=30 for v in rs[-6:-1])
    bb=any(c[i]<=low[i]*1.01 for i in range(len(c)-6,len(c)-1)) and c[-1]>low[-1] and c[-1]>c[-2] and c[-1]<=mid[-1]
    scores={'golden':20 if s50[-1]>s200[-1] and s50[-1]>s50[-6] and s200[-1]>s200[-6] else 15 if s50[-1]>s200[-1] else 0,'rsi':15 if rb else 5 if rs[-1]<30 else 0,'macd':20 if mc and m[-1]>0 and ms[-1]>0 else 15 if mc else 5 if m[-1]>ms[-1] else 0,'obv':15 if ob[-1]>ob[-6] else 0,'bollinger':10 if bb else 0,'stochastic':10 if st else 0}
    notes={'golden':'Recent cross' if gc else 'Both averages rising' if scores['golden']==20 else '50 DMA above 200 DMA' if scores['golden'] else 'Trend gate failed','rsi':'Reversal from 25–30' if rb else 'Oversold' if rs[-1]<30 else 'No oversold reversal','macd':'Bullish crossover above zero' if scores['macd']==20 else 'Recent bullish crossover' if mc else 'MACD above signal' if scores['macd'] else 'No bullish signal','obv':'OBV rising over 5 sessions' if scores['obv'] else 'OBV not rising','bollinger':'Lower-band recovery' if bb else 'No lower-band recovery','stochastic':'Oversold bullish crossover' if st else 'No oversold crossover'}
    return {'date':bars[-1][0][:10],'price':c[-1],'change':round((c[-1]/c[-2]-1)*100,2),'dma50':s50[-1],'dma200':s200[-1],'rsi':rs[-1],'eligible':s50[-1]>s200[-1],'scores':scores,'technicalScore':sum(scores.values()),'notes':notes,'spark':c[-30:]}

def get(url,token=None):
    headers={'User-Agent':'Stocklist/1.0','Accept':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=40) as res: return res.read()

def run():
    token=os.environ.get('ANGEL_ACCESS_TOKEN')
    api_key=os.environ.get('ANGEL_API_KEY')
    if not token or not api_key: raise SystemExit('Add ANGEL_API_KEY and ANGEL_ACCESS_TOKEN as GitHub Actions secrets. No sample rankings will be published.')
    from SmartApi import SmartConnect
    client=SmartConnect(api_key=api_key)
    client.setAccessToken(token)
    instruments=json.loads(get('https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json'))
    token_map={x['symbol']:x['token'] for x in instruments if x.get('exch_seg')=='NSE' and x.get('symbol','').endswith('-EQ')}
    universe=ROOT/'universe.csv'
    if not universe.exists(): raise SystemExit('Add universe.csv with Company Name,Industry,Symbol,ISIN Code from the current Moneycontrol Nifty 500 universe. See README.')
    members=list(csv.DictReader(universe.open()))
    if not 490<=len(members)<=510 or len({s['Symbol'] for s in members})!=len(members): raise SystemExit('Universe must contain 490–510 unique current constituents; verify membership.')
    now=datetime.now(ZoneInfo('Asia/Kolkata')); end=now.date() if (now.hour,now.minute)>=(17,0) else now.date()-timedelta(days=1)
    start=end-timedelta(days=550)
    market_path=ROOT/'market-context.json'; market=json.loads(market_path.read_text()) if market_path.exists() else {}
    old_path=ROOT/'dist/data.json'; old=json.loads(old_path.read_text()) if old_path.exists() else {}; previous={r['symbol']:r for r in old.get('stocks',[])}
    rows=[]; errors=[]
    for member in members:
        symbol=member['Symbol']
        try:
            data=client.getCandleData({'exchange':'NSE','symboltoken':token_map[symbol+'-EQ'],'interval':'ONE_DAY','fromdate':str(start)+' 00:00','todate':str(end)+' 23:59'})
            if not data or not data.get('status'): raise ValueError('Provider rejected candle request')
            bars=sorted(data['data'],key=lambda b:b[0]); row=analyse(bars)
            row.update(symbol=symbol,name=member['Company Name'],sector=member['Industry'])
            factors=market.get(symbol,{})
            valid={k:v for k,v in factors.items() if k in ('sentiment','macro','flows','news') and isinstance(v,dict) and v.get('date')==row['date'] and isinstance(v.get('source'),str) and v['source'].startswith('https://') and isinstance(v.get('positive'),bool)}
            row['marketFactors']=valid; row['marketComplete']=len(valid)==4
            row['scores']['market']=sum(2.5 for v in valid.values() if v['positive'])
            row['score']=row['technicalScore']+row['scores']['market'] if row['marketComplete'] else None
            prev=previous.get(symbol)
            # Reruns of the same session preserve its original comparison.
            if prev and prev['date']==row['date']:
                row['delta']=prev.get('delta'); row['changed']=prev.get('changed',[])
            else:
                row['delta']=row['technicalScore']-prev['technicalScore'] if prev else None
                row['changed']=[row['notes'][k] for k,v in row['scores'].items() if k!='market' and prev and v>prev['scores'].get(k,0)]
            row['stronger']=row['eligible'] and row['delta'] is not None and row['delta']>=10 and bool(row['changed'])
            rows.append(row)
        except Exception as e: errors.append({'symbol':symbol,'error':type(e).__name__})
        time.sleep(1.05)
    if not rows: raise SystemExit('No usable candles returned; previous snapshot preserved. Check token and Actions logs.')
    latest=max(r['date'] for r in rows)
    for r in rows: r['stale']=r['date']!=latest
    payload={'asOf':latest,'generatedAt':now.isoformat(),'provider':'Angel One SmartAPI daily candles','universeSource':'NSE Indices constituent snapshot; Moneycontrol cross-check pending','universeCount':len(members),'stocks':rows,'errors':errors,'status':'partial' if errors else 'ready','weights':WEIGHTS}
    old_path.write_text(json.dumps(payload,indent=2,allow_nan=False))
    print(f'Wrote {len(rows)}/{len(members)} stocks. {len(errors)} excluded. Latest session {latest}.')
if __name__=='__main__': run()
