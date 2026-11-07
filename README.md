# Simulador acelerado de Bolsa Histórica (3 integrantes / redes diferentes)

**Objetivo:** ensayar la estrategia del equipo, no operar en la bolsa oficial. En cada partida, los tres jugadores colaboran **en un solo portafolio** contra cuatro rivales automáticos. El juego comprime 12 momentos en **2 a 18 minutos**; valor inicial idéntico por lógica de generación, noticias ficticias, shocks de precio, liquidación y patrimonio final.

## Mecánicas representadas

- Precios nuevos al iniciar cada momento, noticias públicas, mercado digital de ofertas de rivales, órdenes propias fijas/indexadas, fecha de caducidad de 6 momentos, rango ±20% al publicar, órdenes indexadas por empresa, acciones reservadas.
- Bolsa física con +2.5% compra / −2.5% venta, máximo 500 acciones por empresa/momento y retardo de registro *simulado* de ~4 segundos.
- Solo se opera con efectivo o acciones; las ofertas son de prioridad de llegada. No se enseña el ranking hasta el cierre, gana el patrimonio final y desempata el número de transacciones.
- Las noticias crean pistas y movimientos de mercado sintéticos sobre cuatro casos históricos de referencia, pero **no son series históricas ni simulación estadística calibrada**. Los rivales son bots simplificados. No se ha reproducido la infraestructura real del concurso.

## Tres integrantes desde redes separadas (recomendado)

1. Crea un repositorio **privado** en GitHub con los archivos descomprimidos (incluye `.streamlit/config.toml`, excluye `.streamlit/secrets.toml`).
2. En [Supabase](https://supabase.com) crea un proyecto y ejecuta `schema.sql` en SQL Editor.
3. En [Streamlit Community Cloud](https://share.streamlit.io) publica el repositorio usando `app.py`. Introduce los secretos de `.streamlit/secrets.toml.example` **solo** en el panel privado de Streamlit. No publiques la clave de servicio.
4. Comparte con el equipo la URL `*.streamlit.app` y `TEAM_PIN`. Los tres entran al **mismo ROOM_ID**. Una sola persona conoce el `ADMIN_PIN` y reinicia.
5. El administrador configura segundos/momento y escenario (sorpresa = recomendado), pulsa REINICIAR si desea nueva partida. Todos están en lobby. Pulsen COMENZAR cuando los tres estén listos.

Sin Supabase, el servidor usa SQLite; una única instancia del servidor puede ser visitada desde distintas redes si está publicada, pero **los datos se pueden borrar en reinicios/hibernación**. En nube es preferible Supabase.

## En una computadora (ensayo local)

```bash
python -m pip install -r requirements.txt
```

Crea `.streamlit/secrets.toml` con:

```toml
TEAM_PIN = "codigo-equipo"
ADMIN_PIN = "codigo-admin-distinto"
ROOM_ID = "partida_ensayo"
```

Luego:

```bash
streamlit run app.py
```

## Roles muy sencillos

- **Noticias**: lee el titular automático, selecciona el tema y una empresa, pulsa AVISAR. No compra.
- **Radar de ofertas**: compara precios digitales con mercado, marca una oportunidad y pulsa ENVIAR AL TRADER. No compra.
- **Trader / estratega**: compra ofertas rivales, envía tickets físicos o publica/cancela ventas digitales. Solo esta función ejecuta operaciones simuladas.

Los tres leen el mismo tablero. Los cambios globales aparecen aproximadamente cada dos segundos. No uses este programa para dinero real.

## Evaluación posterior

Al cerrar los 12 momentos aparecen ranking de equipos, número de operaciones, benchmark pasivo (mantener portafolio inicial), caso histórico sintético y auditoría de movimientos. Repite con escenarios diferentes, anotando por qué compraste/vendiste y las operaciones innecesarias.

## Límites y seguridad

- El código NO automatiza ni se conecta a la web o API de la competencia. No replica el comportamiento del organizador ni sus cotizaciones reales.
- Streamlit Community Cloud puede suspender la app por inactividad. Antes de practicar, todos deben ingresar a la URL.
- PIN compartido es un control básico, no sistema de autenticación empresarial; no uses datos reales sensibles.
- `SUPABASE_SECRET_KEY` es **credencial de servidor**: nunca en JavaScript, un HTML, capturas ni código Git. El código SQL limita acceso a `service_role`.
- La latencia de ~4 segundos en tickets físicos es hipótesis para entrenamiento; el manual solo especifica que existe demora, NO cuánto dura.
- El límite de 500 para un mismo ticker/momento se aplica de forma conservadora sumando tickets, dado que la redacción del manual puede interpretarse de forma más amplia.

### Windows - acceso local de un solo equipo

Doble clic en `INICIAR_LOCAL.bat` (necesitas Python 3 e internet para instalar dependencias la primera vez). Crea automáticamente credenciales de **prueba local**: `TEAM_PIN = ensayo123`, `ADMIN_PIN = admin456`. **Nunca publiques estas credenciales**. Este método sirve para una laptop; para tres redes distintas sigue los pasos Supabase + Streamlit Cloud.
