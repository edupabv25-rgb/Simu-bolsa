"""Ensayo acelerado multiusuario de la III Simulación Histórica de Bolsa.
Misma sala de equipo en 3 navegadores / redes; rivales artificiales sintéticos.
"""
from __future__ import annotations
import os, random, time
import pandas as pd
import streamlit as st
from backend import create_store, BusyError
from game import ASSETS, CASE_NAMES, TOTAL_MOMENTS, networth, needs_tick, new_action, free_shares

st.set_page_config(page_title='Bolsa histórica | Ensayo rápido',page_icon='🏛️',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container {padding-top:.75rem;max-width:1200px;padding-bottom:2rem}
h1{font-size:1.65rem!important} h2{font-size:1.20rem!important}
[data-testid="stMetric"]{background:#f3f6f3;padding:11px;border-radius:9px;border:1px solid #d5dfda}
[data-testid="stMetricLabel"]{font-weight:600}
.stAlert{border-radius:9px}
</style>''',unsafe_allow_html=True)

def secret(name,default=None):
    try:return st.secrets.get(name,os.environ.get(name,default))
    except Exception:return os.environ.get(name,default)

team_pin=secret('TEAM_PIN'); admin_pin=secret('ADMIN_PIN');room=secret('ROOM_ID','bolsa_practica_1')
if not team_pin or team_pin=='CODIGO_DEL_EQUIPO':
    st.error('Configuración inicial: añade TEAM_PIN a .streamlit/secrets.toml (local) o Secrets (nube).')
    st.code('TEAM_PIN = "clave-para-equipo"\nADMIN_PIN = "clave-solo-organizador"\nROOM_ID = "bolsa_practica_1"',language='toml')
    st.stop()

st.title('Mesa de entrenamiento · Bolsa histórica')
st.caption('**SIMULACIÓN FICTICIA ACELERADA.** Inspirada en las reglas del manual; no reproduce cotizaciones históricas reales ni se conecta a la bolsa oficial.')
if not st.session_state.get('logged_in'):
    with st.form('login'):
        c1,c2=st.columns(2)
        code=c1.text_input('Clave del equipo',type='password')
        nick=c2.text_input('Tu nombre o iniciales',max_chars=28)
        role=st.selectbox('Tu función', ['Noticias', 'Radar de ofertas', 'Trader / estratega'])
        if st.form_submit_button('Entrar al ensayo',type='primary'):
            if code!=team_pin:st.error('Clave incorrecta')
            elif not nick.strip():st.warning('Indica iniciales')
            else:
                st.session_state.logged_in=True
                st.session_state.nick=nick.strip()
                st.session_state.role=role
                st.rerun()
    st.stop()

config={k:secret(k) for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_SERVICE_ROLE_KEY']}
store,cloud=create_store(config)

def read():
    try:return store.read(room)[1]
    except Exception as ex:
        st.error('No pude leer la sala. Verifica Supabase y que hayas ejecutado schema.sql: '+str(ex))
        st.stop()

def dispatch(kind,admin=False,**kw):
    action=new_action(kind,'ADMIN' if admin else st.session_state.nick,**kw)
    try:
        _,s=store.apply(room,action)
        st.toast('Acción registrada en la sala',icon='✅')
        return s
    except (ValueError,BusyError) as ex:st.warning(str(ex))
    except Exception as ex:st.error('No se guardó. Comprueba el historial antes de reintentar. '+str(ex))
    return None

def offer_caption(o,prices):
    k=o['ticker']; reference=prices[k]
    disc=(1-o['price']/reference)*100 if reference>0 else float('nan')
    return f'{k} · {o["remaining"]} acc. @ {o["price"]:.2f} · descuento {disc:+.1f}% · {o["mode"]}'

with st.sidebar:
    st.write('**'+st.session_state.nick+'**')
    role=st.selectbox('Tu función', ['Noticias','Radar de ofertas','Trader / estratega'],
                      index=['Noticias','Radar de ofertas','Trader / estratega'].index(st.session_state.role))
    st.session_state.role=role
    st.caption('Una sola sala; 3 dispositivos. La partida se sincroniza entre navegadores.')
    if not cloud:st.warning('SQLite local. En nube funciona durante la sesión, pero un reinicio puede borrar el ensayo. Se recomienda Supabase.')
    if st.button('Refrescar pantalla',use_container_width=True):st.rerun()
    with st.expander('Administración · nueva partida'):
        admin_code=st.text_input('PIN del administrador',type='password',key='admin_code')
        if admin_pin and admin_code==admin_pin:
            seconds=st.select_slider('Segundos por momento',options=[10,15,20,30,45,60,90],value=20)
            sc_options={'Sorpresa (aleatoria)':'aleatorio',**{v:k for k,v in CASE_NAMES.items()}}
            episode=st.selectbox('Historia a ensayar',list(sc_options))
            st.caption('La historia no se revela a los integrantes hasta el final. 12 momentos, por ejemplo 20 s × 12 = 4 min.')
            if st.button('REINICIAR toda la sala',type='secondary',use_container_width=True):
                if dispatch('reset',admin=True,seed=random.SystemRandom().randint(1,99999999),seconds=seconds,scenario=sc_options[episode]):st.rerun()
        else:st.caption('Solo el administrador puede reiniciar el simulador.')
    if st.button('Cerrar mi sesión',use_container_width=True):
        st.session_state.logged_in=False;st.rerun()

@st.fragment(run_every='2s')
def simulator():
    s=read()
    # A single server executes tick via compare-and-swap; concurrent browsers converge.
    if needs_tick(s,time.time()):
        x=dispatch('tick')
        if x is not None:s=x
    now=time.time()
    status=s['status']
    if status=='lobby':
        st.info('🟦 Sala preparada. Entra con los 3 dispositivos y comienza cuando todos estén listos.')
        a,b,c=st.columns(3)
        a.metric('Duración',f'{TOTAL_MOMENTS*s["moment_seconds"]//60} min {TOTAL_MOMENTS*s["moment_seconds"]%60} s')
        b.metric('Activos disponibles',len(s['prices']))
        c.metric('Capital inicial',f'{s["initial_value"]:,.2f}')
        if st.button('▶ COMENZAR PARTIDA',type='primary',use_container_width=True):
            if dispatch('start'):st.rerun()
        st.caption('Todos juegan EN EL MISMO EQUIPO contra 4 rivales automáticos. El ranking permanece oculto hasta el cierre.')
        return
    if status=='running':
        next_ts=s['started_at']+s['moment']*s['moment_seconds']
        seconds_left=max(0,int(next_ts-now+0.99))
        st.progress(min(1,max(0,(now-s['started_at'])/(TOTAL_MOMENTS*s['moment_seconds']))),
                    text=f'EN JUEGO · Momento {s["moment"]}/{TOTAL_MOMENTS} · próximo cambio en {seconds_left} s')
    else:
        st.success('🏁 Bolsa cerrada · resultado final calculado por patrimonio + desempate de operaciones')
    a,b,c,d=st.columns(4)
    a.metric('Patrimonio',f'{networth(s):,.2f}',f'{(networth(s)/s["initial_value"]-1)*100:+.2f}%')
    b.metric('Efectivo',f'{s["cash"]:,.2f}')
    c.metric('Operaciones',s['trade_count'])
    d.metric('Órdenes físicas pendientes',len(s['pending']))

    if s['news']:
        headline=s['news'][0]
        st.info(f'**NOTICIA DEL MOMENTO {headline["moment"]}** · {headline["text"]}')
    if s['alerts']:
        alert=s['alerts'][0]
        st.caption(f'📣 Alerta de {alert["actor"]} · momento {alert["moment"]}: **{alert["text"]}**')

    px=s['prices']
    rows=[]
    for k,p in px.items():
        last=s['prev'][k]
        rows.append({'Acción':k,'Empresa':ASSETS[k][0],'Sector':ASSETS[k][1],
          'Precio':p,'Var. %':round((p/last-1)*100,1) if last else 0,
          'Acciones equipo':s['qty'][k],'Libres para ofertar':free_shares(s,k),
          'Valor':round(s['qty'][k]*p,2)})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,
                 column_config={'Precio':st.column_config.NumberColumn(format='%.2f'),
                                'Var. %':st.column_config.NumberColumn(format='%.1f%%'),
                                'Valor':st.column_config.NumberColumn(format='%.2f')})

    if status=='finished':
        st.subheader('Resultado de la prueba')
        rank=s['finished_rank'] or []
        rankdf=pd.DataFrame([{'Puesto':i+1,'Equipo':x['name'],'Patrimonio':x['value'],'Operaciones':x['trades']} for i,x in enumerate(rank)])
        st.dataframe(rankdf,hide_index=True,use_container_width=True)
        holding=s['initial_cash']+sum(s['initial_qty'][k]*s['prices'][k] for k in s['prices'])
        st.write('**Episodio sintético utilizado:** '+CASE_NAMES[s['scenario']])
        st.write(f'**Benchmark mantener sin operar:** {holding:,.2f} · **Tu resultado:** {networth(s):,.2f} · **Diferencia:** {networth(s)-holding:+,.2f}')
        st.caption('Este benchmark utiliza las mismas acciones iniciales y precios finales, sin decisiones de inversión. Los rivales son artificiales; ganar este ensayo no predice ganar el concurso.')
        with st.expander('Auditoría de la partida',expanded=True):
            st.write('**Tus operaciones**')
            st.dataframe(pd.DataFrame(s['trades']),hide_index=True,use_container_width=True)
            st.write('**Eventos**')
            st.dataframe(pd.DataFrame(s['events']),hide_index=True,use_container_width=True)
        return

    if st.session_state.role=='Noticias':
        st.subheader('Tu misión: leer la noticia y avisar en segundos')
        st.caption('La primera persona NO compra. Lee, señala el riesgo y avisa al Trader.')
        with st.form('news_signal',clear_on_submit=True):
            cl=st.selectbox('Señal principal',['Riesgo de quiebra / fraude','Crisis bancaria o crediticia',
                'Suben metales','Caen metales','Petróleo sube','Petróleo baja','Banco central / tasas',
                'Rebote / rescate','No está claro'])
            target=st.selectbox('Empresa que parece afectada',['Por investigar']+list(px))
            direction=st.radio('¿Impacto probable?',['Negativo','Positivo','Dudoso'],horizontal=True)
            if st.form_submit_button('📣 AVISAR AL EQUIPO',type='primary',use_container_width=True):
                msg=f'{direction.upper()} · {cl} · {target}'
                if dispatch('alert',text=msg):st.rerun()
        st.caption('Ejemplo: «NEGATIVO · crisis bancaria · BANCO». No necesitas estimar porcentajes.')

    elif st.session_state.role=='Radar de ofertas':
        st.subheader('Tu misión: encontrar precios ventajosos')
        st.caption('Compara la OFERTA DIGITAL con el precio de mercado. Marca oportunidades para revisión, sin decidir la compra.')
        offers=sorted([o for o in s['offers'] if o['remaining']>0],key=lambda o:(o['price']/px[o['ticker']]))
        if not offers:st.warning('No quedan ofertas rivales, espera el siguiente momento.')
        else:
            offerrows=[{'Código':o['id'][:7],'Acción':o['ticker'],'Precio oferta':o['price'],
               'Precio mercado':px[o['ticker']], 'Descuento %':round(100*(1-o['price']/px[o['ticker']]),1),
               'Cantidad':o['remaining'],'Tipo':o['mode'],'Creada momento':o['created']} for o in offers]
            st.dataframe(pd.DataFrame(offerrows),hide_index=True,use_container_width=True)
            st.caption('Descuento positivo = oferta más barata que el último precio publicado. NO garantiza que el precio final sea superior.')
            selected=st.selectbox('Oportunidad a informar',offers,
                   format_func=lambda o: offer_caption(o,px),
                   key='opportunity_'+str(s['moment']))
            if st.button('📣 ENVIAR AL TRADER',type='primary',use_container_width=True):
                discount=(1-selected['price']/px[selected['ticker']])*100
                if dispatch('alert',text=f'REVISAR {selected["ticker"]}: oferta {selected["price"]:.2f}, mercado {px[selected["ticker"]]:.2f}, descuento {discount:+.1f}%, volumen {selected["remaining"]}'):
                    st.rerun()
    else:
        st.subheader('Tu misión: elegir y ejecutar órdenes simuladas')
        st.caption('Solo aquí se compran/venden acciones. No opera en la plataforma oficial.')
        tab1,tab2,tab3=st.tabs(['Comprar ofertas digitales','Ticket físico','Vender / anular ofertas'])
        with tab1:
            offers=sorted([o for o in s['offers'] if o['remaining']>0],key=lambda o:o['price']/px[o['ticker']])
            if not offers:st.info('No hay ofertas disponibles; aparecerán otras en próximos momentos.')
            else:
                selected=st.selectbox('Oferta en venta (por orden de descuento)',offers,
                          format_func=lambda o: offer_caption(o,px),
                          key='buy_offer_'+str(s['moment']))
                st.caption(f'Precio publicado: {px[selected["ticker"]]:.2f} · Precio ofrecido: {selected["price"]:.2f} · comisión digital: no indicada por el manual.')
                maxq=min(selected['remaining'],int(s['cash']/selected['price']))
                if maxq<1:st.warning('No tienes efectivo para comprar esta oferta.')
                else:
                    amount=st.number_input('Acciones que compras',min_value=1,max_value=maxq,value=min(30,maxq),step=1,key='bq'+selected['id'])
                    st.write(f'**Costo:** {amount*selected["price"]:,.2f} · Efectivo restante (si se ejecuta): {s["cash"]-amount*selected["price"]:,.2f}')
                    if st.button('COMPRAR AHORA EN EL ENSAYO',type='primary',use_container_width=True):
                        if dispatch('buy_offer',offer_id=selected['id'],qty=amount):st.rerun()
        with tab2:
            p1,p2,p3=st.columns([1,1,1]);tkr=p1.selectbox('Acción',list(px),key='physical_stock')
            side=p2.selectbox('Orden',['COMPRA','VENTA'],key='physical_side')
            maxq=min(500, int(s['cash']/(px[tkr]*1.025))) if (side=='COMPRA' and px[tkr]>0) else (min(500,free_shares(s,tkr)) if px[tkr]>0 else 0)
            n=p3.number_input('Cantidad',min_value=1,max_value=max(1,maxq),value=min(max(1,maxq),30),step=1)
            st.caption(f'Cotización ahora: {px[tkr]:.2f}. Comisión física 2.5% y registro demorado ~4 s. Tope 500 acciones por empresa/momento (regla conservadora).')
            if maxq<=0:st.warning('No hay saldo o acciones libres suficientes.')
            elif st.button('ENVIAR TICKET FÍSICO',type='primary',use_container_width=True):
                if dispatch('physical',ticker=tkr,side=side,qty=n):st.rerun()
        with tab3:
            k=st.selectbox('Acción a ofertar',list(px),key='sell_stock')
            available=free_shares(s,k)
            st.caption(f'Tienes {s["qty"][k]} acciones. Libres para nuevas ofertas: {available}. Las ofertadas siguen valorizándose hasta venderse.')
            if available>0 and px[k]>0:
                p1,p2,p3=st.columns(3)
                mode=p1.selectbox('Tipo',['Indexada','Fija'])
                percent=p2.number_input('Sobre el mercado, %',min_value=-20.0,max_value=20.0,value=5.0,step=1.0,format='%.1f')
                nq=p3.number_input('Acciones a ofrecer',min_value=1,max_value=available,value=min(40,available),step=1)
                st.write(f'Precio inicial de oferta: **{px[k]*(1+percent/100):.2f}**. '+('Indexada: se mueve con cotización.' if mode=='Indexada' else 'Fija: conserva precio hasta 6 momentos.'))
                if st.button('PUBLICAR VENTA DE ENSAYO',use_container_width=True):
                    if dispatch('offer_sell',ticker=k,mode=mode,pct=percent,qty=nq):st.rerun()
            if s['own_offers']:
                st.write('**Tus ofertas abiertas**')
                for offer in s['own_offers']:
                    x,y=st.columns([5,1])
                    x.write(f'{offer["ticker"]} · {offer["remaining"]} acc. · {offer["mode"]} · {offer["price"]:.2f} ({offer["pct"]:+g}%)')
                    if y.button('Anular',key='cancel_'+offer['id']):
                        if dispatch('cancel_offer',offer_id=offer['id']):st.rerun()

    with st.expander('Últimos movimientos y órdenes pendientes'):
        for p in s['pending']:
            st.warning(f'Ticket {p["side"]} de {p["qty"]} {p["ticker"]} pendiente (puede registrarse a otro precio)')
        for item in s['events'][:14]:
            st.caption(f'M{item["moment"]} · {item["actor"]} · {item["text"]}')
    st.caption('Los precios, shocks, volúmenes y conductas rivales de este ensayo son datos sintéticos. La plataforma oficial puede comportarse de forma diferente.')

simulator()
