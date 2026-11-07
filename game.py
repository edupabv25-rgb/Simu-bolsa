"""Motor de simulación bursátil sintética, inspirado EXCLUSIVAMENTE en reglas operativas del manual.
No afirma reconstruir los precios históricos ni la dinámica verdadera de organizadores.
Las transiciones son puras y reproducibles mediante una semilla.
"""
from __future__ import annotations
from copy import deepcopy
import math, random, time, uuid

TOTAL_MOMENTS = 12
ASSETS = {
    'COBRE': ('Minera cuprífera', 'Metales', 42.0),
    'ORO': ('Productora aurífera', 'Oro', 35.0),
    'BANCO': ('Banco comercial', 'Banca', 19.0),
    'VIVIEN': ('Inmobiliaria', 'Construcción', 24.0),
    'PETRO': ('Productora energética', 'Petróleo', 30.0),
    'INDUS': ('Industria manufacturera', 'Industria', 20.0),
    'TECH': ('Empresa tecnológica', 'Tecnología', 28.0),
    'TRANS': ('Empresa de transporte', 'Transporte', 16.0),
    'ALIM': ('Consumo esencial', 'Consumo', 25.0),
}
INITIAL_QTY = {'COBRE':180, 'ORO':140, 'BANCO':300, 'VIVIEN':180, 'PETRO':110,
               'INDUS':130, 'TECH':120, 'TRANS':100, 'ALIM':100}
INITIAL_CASH = 25000.0
CASE_NAMES = {'crisis08':'Crisis de crédito (inspirado en 2008)',
              'metales':'Boom y reversión de metales',
              'energia':'Shock de petróleo y tasas',
              'tecnologia':'Burbuja tecnológica y corrección'}
# impact shocks are scenario-design assumptions in %, NOT actual historic returns or forecasts
CASES = {
 'crisis08': {
   2: ('Aumentan incumplimientos hipotecarios; analistas alertan sobre exposición bancaria.', {}),
   3: ('Se restringe el crédito interbancario. Caen valores financieros.', {'BANCO':-12,'VIVIEN':-7,'INDUS':-3,'TECH':-2}),
   5: ('Entidad relevante admite pérdidas mayores que las reportadas.', {'BANCO':-14,'VIVIEN':-5,'COBRE':-3}),
   7: ('Autoridad anuncia apoyo a la liquidez; aún persiste temor a insolvencia.', {'BANCO':5,'VIVIEN':2,'ORO':3}),
   9: ('Caen perspectivas de demanda global por contracción crediticia.', {'COBRE':-9,'PETRO':-7,'INDUS':-6,'TRANS':-5}),
   10: ('BANCO anuncia liquidación. La acción deja de tener valor en el ensayo.', {'BANCO':-100}),
   11: ('Persiste la aversión al riesgo; los activos refugio reciben demanda.', {'ORO':3}),
 },
 'metales': {
   2: ('Aumentan pedidos industriales internacionales de cobre y zinc.', {}),
   3: ('Los compradores elevan compras de cobre; productores exportadores se benefician.', {'COBRE':10,'INDUS':2,'BANCO':2}),
   5: ('Oferta minera se retrasa por problemas de producción.', {'COBRE':8,'ORO':1}),
   7: ('Se desacelera demanda asiática; mercado reconsidera expectativas.', {'COBRE':-10,'INDUS':-4,'PETRO':-3}),
   9: ('Nuevo paquete de infraestructura fortalece las perspectivas de metales.', {'COBRE':7,'VIVIEN':4,'INDUS':3}),
   11: ('Incertidumbre cambiaria impulsa búsqueda de oro.', {'ORO':8,'COBRE':-2}),
 },
 'energia': {
   2: ('Se intensifican riesgos geopolíticos sobre suministro de crudo.', {}),
   3: ('Restricción de suministro impulsa precios de hidrocarburos.', {'PETRO':13,'TRANS':-8,'INDUS':-4}),
   5: ('Inflación sorprende al alza; el banco central anuncia endurecimiento.', {'VIVIEN':-8,'TECH':-7,'BANCO':-3,'ALIM':-2}),
   7: ('Productores anuncian ampliación de oferta de petróleo.', {'PETRO':-10,'TRANS':5}),
   9: ('Banco central mantiene tasas elevadas; persiste freno a demanda.', {'VIVIEN':-5,'TECH':-4,'INDUS':-4}),
   11: ('Se negocia solución a las restricciones energéticas.', {'PETRO':-5,'TRANS':5}),
 },
 'tecnologia': {
   2: ('Empresas tecnológicas cotizan a múltiplos récord; preocupación por valoraciones.', {}),
   3: ('Tecnológica líder decepciona en resultados; sector corrige.', {'TECH':-13,'BANCO':-2}),
   5: ('Aumentan despidos tecnológicos y revisiones de ingresos.', {'TECH':-12,'INDUS':-2}),
   7: ('Se anuncia una posible rebaja de tasas para apoyar actividad.', {'TECH':5,'VIVIEN':4,'BANCO':2}),
   9: ('Fraude contable alcanza a una empresa del sector tecnológico.', {'TECH':-16}),
   11: ('Capital rota hacia consumo defensivo y productoras de oro.', {'ALIM':5,'ORO':5,'TECH':-3}),
 }
}

def uid(): return uuid.uuid4().hex

def money(value): return round(float(value)+1e-9,2)

def initial_state(seed:int=20261107, seconds:int=20, scenario:str='aleatorio'):
    if scenario == 'aleatorio':
        scenario = random.Random(int(seed)).choice(list(CASES))
    if scenario not in CASES: raise ValueError('Escenario inválido')
    if not 10 <= int(seconds) <= 90: raise ValueError('Duración fuera de rango')
    px = {k:info[2] for k, info in ASSETS.items()}
    starting_value = money(INITIAL_CASH + sum(INITIAL_QTY[k]*v for k,v in px.items()))
    # rival base patrimonies intentionally near team initial level; deterministic exposures
    rgen = random.Random(seed+109)
    bots=[]
    for idx,style in enumerate(['Rival A · Momentum','Rival B · Defensivo','Rival C · Agresivo','Rival D · Diversificado']):
        q={k:rgen.randint(50,220) for k in ASSETS}
        stocks=sum(q[k]*px[k] for k in ASSETS)
        q_cash=money(max(0,starting_value-stocks))
        # normalize if rivals over-start: scale holdings down
        if stocks > starting_value*.9:
            q={k:int(v*.7) for k,v in q.items()}
            q_cash=money(starting_value-sum(q[k]*px[k] for k in ASSETS))
        bots.append({'name':style,'cash':q_cash,'qty':q,'trades':0})
    return {
      'seed':int(seed),'scenario':scenario,'moment_seconds':int(seconds),
      'status':'lobby','moment':1,'started_at':None,'closed_at':None,
      'prices':px,'prev':dict(px),'cash':INITIAL_CASH,'qty':dict(INITIAL_QTY),
      'initial_value':starting_value,'initial_cash':INITIAL_CASH,'initial_qty':dict(INITIAL_QTY),
      'bots':bots,'offers':[],'own_offers':[],'pending':[],
      'news':[{'moment':1,'text':'Se abre la simulación. Los precios son ficticios y seguirán una historia económica sintética.'}],
      'alerts':[],'events':[], 'trades':[], 'seq':0,
      'physical_usage':{},'trade_count':0,'finished_rank':None,
      'case_revealed':False,'price_history':[{'moment':1,'prices':dict(px)}]
    }

def networth(s): return money(s['cash']+sum(q*s['prices'][k] for k,q in s['qty'].items()))
def botworth(bot, prices): return money(bot['cash']+sum(bot['qty'].get(k,0)*prices[k] for k in prices))
def free_shares(s,k):
    reserved = sum(o['remaining'] for o in s['own_offers'] if o['ticker']==k and o['remaining']>0)
    pending = sum(p['qty'] for p in s['pending'] if p['side']=='VENTA' and p['ticker']==k)
    return s['qty'][k]-reserved-pending

def event(s,txt,actor='SISTEMA'):
    s['seq'] += 1
    s['events'].insert(0, {'id':s['seq'],'moment':s['moment'],'actor':actor,'text':txt})
    s['events']=s['events'][:120]

def make_bot_offers(s, moment):
    rng=random.Random(s['seed']*97 +moment*67+77)
    for _ in range(5):
        k=rng.choice([key for key,p in s['prices'].items() if p>0])
        seller=rng.randrange(len(s['bots']))
        bot=s['bots'][seller]
        reserved=sum(x['remaining'] for x in s['offers'] if x['seller']==seller and x['ticker']==k)
        available=bot['qty'][k]-reserved
        if available<=0:continue
        qty=min(available,rng.randint(14,125))
        if qty<=0:continue
        # discount quote distribution including fixed stale offers -> price-difference arbitrage
        mode='Fija' if rng.random()<.72 else 'Indexada'
        pct=rng.choice([-9,-6,-4,-2,0,2,3,5,8,12,18])
        offer={'id':uid(),'ticker':k,'seller':seller,'mode':mode,
               'pct':pct,'price':money(s['prices'][k]*(1+pct/100)),
               'remaining':qty,'created':moment,'expires':moment+6 if mode=='Fija' else None}
        s['offers'].append(offer)
    # Ensure bounded snapshot, dropping expired and exhausted
    s['offers']=[o for o in s['offers'] if o['remaining']>0][-100:]

def execute_pending(s, ts):
    left=[]
    for p in s['pending']:
        if p['due']>ts:
            left.append(p);continue
        k=p['ticker']; q=p['qty']; price=s['prices'][k]
        gross=money(q*price); fee=money(gross*.025)
        if price<=0:
            event(s,f'✗ Ticket {p["side"]} {k} rechazado: empresa sin cotización positiva',p['actor'])
            continue
        if p['side']=='COMPRA' and s['cash']+1e-7 >= gross+fee:
            s['cash']=money(s['cash']-gross-fee);s['qty'][k]+=q
            s['trade_count']+=1
            s['trades'].insert(0,{'moment':s['moment'],'side':'COMPRA','ticker':k,'qty':q,'price':price,'fee':fee,'venue':'Física'})
            event(s,f'✓ Física: compra {q} {k} a {price:.2f}; comisión {fee:.2f}',p['actor'])
        elif p['side']=='VENTA' and free_shares_with_pending(s,k,ignore=p['id'])>=q:
            s['cash']=money(s['cash']+gross-fee);s['qty'][k]-=q
            s['trade_count']+=1
            s['trades'].insert(0,{'moment':s['moment'],'side':'VENTA','ticker':k,'qty':q,'price':price,'fee':fee,'venue':'Física'})
            event(s,f'✓ Física: venta {q} {k} a {price:.2f}; comisión {fee:.2f}',p['actor'])
        else:
            event(s,f'✗ Ticket {p["side"]} {k} rechazado al registrar (saldo/acciones insuficientes)',p['actor'])
    s['pending']=left
    s['trades']=s['trades'][:180]

def free_shares_with_pending(s,k,ignore=None):
    offered=sum(o['remaining'] for o in s['own_offers'] if o['ticker']==k)
    reserved=sum(p['qty'] for p in s['pending'] if p['side']=='VENTA' and p['ticker']==k and p['id']!=ignore)
    return s['qty'][k]-offered-reserved

def progress_moment(s,m):
    s['moment']=m
    old=dict(s['prices']);s['prev']=old
    rng=random.Random(s['seed']*100003+m*1039)
    for k in old:
        # small normal micro-moves; exact news shock applied in current moment
        move=rng.gauss(0, .012)
        shock=CASES[s['scenario']].get(m)
        if shock:move+=shock[1].get(k,0)/100
        if old[k]<=0 or (shock and shock[1].get(k,0)<=-100):s['prices'][k]=0.0
        else:s['prices'][k]=money(max(.01,old[k]*(1+move)))
    shock=CASES[s['scenario']].get(m)
    if shock:
        s['news'].insert(0,{'moment':m,'text':shock[0]})
        s['news']=s['news'][:15]
    # rules: fixed listings expire after 6 moments; indexed listings reprice automatically
    s['offers']=[o for o in s['offers'] if o['remaining']>0 and s['prices'][o['ticker']]>0 and (o['expires'] is None or m<o['expires'])]
    s['own_offers']=[o for o in s['own_offers'] if o['remaining']>0 and s['prices'][o['ticker']]>0 and (o['expires'] is None or m<o['expires'])]
    for offer in s['offers']+s['own_offers']:
        if offer['mode']=='Indexada':offer['price']=money(s['prices'][offer['ticker']]*(1+offer['pct']/100))
    # Synthetic opponents may buy team's digital listings if advantageous and sufficiently liquid.
    rng2=random.Random(s['seed']+99991*m)
    for offer in s['own_offers'][:]:
        k=offer['ticker'];pct=(offer['price']/max(.01,s['prices'][k])-1)*100
        if pct <= rng2.choice([-6,-4,-2,0,1]) and offer['remaining']>0:
            bot=rng2.choice(s['bots']);amount=min(offer['remaining'],rng2.randint(10,100),int(bot['cash']/offer['price']))
            if amount>0:
                income=money(amount*offer['price']);s['cash']=money(s['cash']+income);s['qty'][k]-=amount
                bot['cash']=money(bot['cash']-income);bot['qty'][k]+=amount;bot['trades']+=1
                s['trade_count']+=1;offer['remaining']-=amount
                s['trades'].insert(0,{'moment':m,'side':'VENTA','ticker':k,'qty':amount,'price':offer['price'],'fee':0,'venue':'Digital'})
                event(s,f'Rival aceptó tu oferta: venta {amount} {k} a {offer["price"]:.2f}')
    s['own_offers']=[o for o in s['own_offers'] if o['remaining']>0]
    make_bot_offers(s,m)
    # Rivals rebalance occasionally, no leakage of their portfolios until closure
    for idx,bot in enumerate(s['bots']):
        rng3=random.Random(s['seed']*89+m*31+idx)
        if rng3.random()<.62:
            k=rng3.choice([key for key,p in s['prices'].items() if p>0]);qty=rng3.randint(8,55);price=s['prices'][k]
            sector=ASSETS[k][1];fav=(s['scenario']=='metales' and sector=='Metales') or (s['scenario']=='crisis08' and sector=='Oro')
            buy=(rng3.random()<(.62 if fav else .38))
            if buy and bot['cash']>=price*qty:
                bot['cash']=money(bot['cash']-price*qty);bot['qty'][k]+=qty;bot['trades']+=1
            elif not buy:
                reserved=sum(x['remaining'] for x in s['offers'] if x['seller']==idx and x['ticker']==k)
                if bot['qty'][k]-reserved>=qty:
                    bot['cash']=money(bot['cash']+price*qty*.975);bot['qty'][k]-=qty;bot['trades']+=1
    s['price_history'].append({'moment':m,'prices':dict(s['prices'])})
    event(s,f'Nuevo momento {m}; precios y ofertas actualizados')

def settle(s,ts):
    if s['status']!='running':return
    # full game time measured from start; no manual price or news anticipation
    target=min(TOTAL_MOMENTS,1+max(0,int((ts-s['started_at'])//s['moment_seconds'])))
    while s['moment']<target:
        progress_moment(s,s['moment']+1)
    execute_pending(s,ts)
    if ts >= s['started_at']+TOTAL_MOMENTS*s['moment_seconds']:
        for p in s['pending']:
            event(s,f'✗ Ticket {p["side"]} {p["ticker"]} no registrado antes del cierre',p['actor'])
        s['pending']=[]
        s['status']='finished';s['closed_at']=ts;s['case_revealed']=True
        finish=[{'name':'Tu equipo','value':networth(s),'trades':s['trade_count']}]
        finish += [{'name':bot['name'],'value':botworth(bot,s['prices']),'trades':bot['trades']} for bot in s['bots']]
        finish.sort(key=lambda a:(-a['value'],a['trades']))
        s['finished_rank']=finish
        event(s,'Bolsa cerrada. Ranking final publicado')

def apply_action(original, action):
    s=deepcopy(original);typ=action['type'];ts=float(action.get('ts',time.time()))
    actor=str(action.get('actor','Equipo'))[:35]
    if typ=='reset':
        if actor!='ADMIN':raise ValueError('Solo el administrador puede reiniciar')
        new=initial_state(int(action['seed']),int(action['seconds']),action.get('scenario','aleatorio'))
        event(new,'Se reinició la partida; escenario y precios de la prueba renovados')
        return new
    if typ=='start':
        if s['status']!='lobby':raise ValueError('La partida ya comenzó')
        s['status']='running';s['started_at']=ts
        make_bot_offers(s,1)
        event(s,'¡Comienza la partida! Las ofertas de los rivales están disponibles.',actor)
        return s
    settle(s,ts)
    if typ=='tick':return s
    if s['status']!='running':raise ValueError('Solo se puede operar con la bolsa abierta')
    if typ=='alert':
        txt=str(action.get('text','')).strip()[:200]
        if not txt:raise ValueError('Escribe una observación')
        s['alerts'].insert(0,{'moment':s['moment'],'actor':actor,'text':txt})
        s['alerts']=s['alerts'][:35]
        event(s,'Alerta del equipo: '+txt,actor)
    elif typ=='buy_offer':
        offer=next((o for o in s['offers'] if o['id']==action['offer_id'] and o['remaining']>0),None)
        if not offer:raise ValueError('Oferta agotada/no disponible. Actualiza antes de comprar')
        qty=int(action['qty']);p=offer['price'];total=money(qty*p)
        if qty<=0 or qty>offer['remaining']:raise ValueError('Cantidad inválida para esta oferta')
        if total>s['cash']+1e-7:raise ValueError('Efectivo insuficiente')
        k=offer['ticker'];seller=s['bots'][offer['seller']]
        s['cash']=money(s['cash']-total);s['qty'][k]+=qty
        seller['cash']=money(seller['cash']+total);seller['qty'][k]-=qty;seller['trades']+=1
        offer['remaining']-=qty;s['trade_count']+=1
        s['trades'].insert(0,{'moment':s['moment'],'side':'COMPRA','ticker':k,'qty':qty,'price':p,'fee':0,'venue':'Digital'})
        event(s,f'Compra digital {qty} {k} @ {p:.2f}; descuento vs mercado {(1-p/s["prices"][k])*100:+.1f}%',actor)
    elif typ=='offer_sell':
        k=str(action['ticker']);mode=str(action['mode']);qty=int(action['qty']);delta=float(action['pct'])
        if k not in ASSETS:raise ValueError('Empresa inválida')
        if s['prices'][k]<=0:raise ValueError('Este valor cotiza en 0: no admite nuevas ofertas')
        if qty<=0 or qty>free_shares(s,k):raise ValueError('No tienes suficientes acciones libres')
        if not -20<=delta<=20:raise ValueError('Oferta fuera del rango ±20%')
        if mode not in ('Fija','Indexada'):raise ValueError('Tipo de oferta inválido')
        if mode=='Indexada' and any(o['mode']=='Indexada' and o['ticker']==k for o in s['own_offers']):
            raise ValueError('Máximo una oferta indexada abierta por empresa')
        new={'id':uid(),'ticker':k,'mode':mode,'pct':delta,'price':money(s['prices'][k]*(1+delta/100)),
             'remaining':qty,'created':s['moment'],'expires':s['moment']+6 if mode=='Fija' else None}
        s['own_offers'].append(new)
        event(s,f'Publicaste venta {mode.lower()}: {qty} {k}, {delta:+g}% del mercado',actor)
    elif typ=='cancel_offer':
        before=len(s['own_offers']);s['own_offers']=[o for o in s['own_offers'] if o['id']!=action['offer_id']]
        if before==len(s['own_offers']):raise ValueError('La oferta ya fue retirada o ejecutada')
        event(s,'Cancelaste una oferta digital propia',actor)
    elif typ=='physical':
        k=str(action['ticker']);side=str(action['side']);qty=int(action['qty'])
        if k not in ASSETS or side not in ('COMPRA','VENTA'):raise ValueError('Ticket inválido')
        if s['prices'][k]<=0:raise ValueError('Empresa liquidada o cotización 0; no admite tickets')
        if qty<=0 or qty>500:raise ValueError('Tope físico: 500 acciones por empresa y momento')
        key=f'{s["moment"]}:{k}'
        if s['physical_usage'].get(key,0)+qty>500:raise ValueError('Ya alcanzaste 500 acciones físicas de esta empresa en este momento')
        if side=='VENTA' and qty>free_shares(s,k):raise ValueError('Acciones libres insuficientes')
        if side=='COMPRA' and (s['cash'] < qty*s['prices'][k]*1.025):raise ValueError('Efectivo insuficiente al enviar ticket')
        s['physical_usage'][key]=s['physical_usage'].get(key,0)+qty
        s['pending'].append({'id':uid(),'side':side,'ticker':k,'qty':qty,'actor':actor,
                             'moment':s['moment'],'due':ts+4})
        event(s,f'Ticket físico {side.lower()} {qty} {k}; se registra en ~4 segundos al precio entonces vigente',actor)
    else:raise ValueError('Acción no reconocida')
    s['trades']=s['trades'][:180]
    return s

def needs_tick(s,ts):
    return s['status']=='running' and (
      ts>=s['started_at']+TOTAL_MOMENTS*s['moment_seconds'] or
      1+int(max(0,ts-s['started_at'])//s['moment_seconds'])>s['moment'] or
      any(p['due']<=ts for p in s['pending'])
    )

def new_action(kind,actor='Equipo',**kwargs):
    return {'id':uid(),'type':kind,'actor':actor,'ts':time.time(),**kwargs}
