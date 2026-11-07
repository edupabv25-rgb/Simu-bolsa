@echo off
setlocal
cd /d "%~dp0"
if not exist ".streamlit\secrets.toml" (
  echo Creando PINs de SOLO ensayo local. NO publiques este archivo.
  > ".streamlit\secrets.toml" echo TEAM_PIN = "ensayo123"
  >> ".streamlit\secrets.toml" echo ADMIN_PIN = "admin456"
  >> ".streamlit\secrets.toml" echo ROOM_ID = "mi_sala_local"
)
echo.
echo PIN para entrar: ensayo123
 echo PIN administrador: admin456
 echo.
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo No se pudo instalar. Verifica Python 3 y el lanzador py.
  pause
  exit /b 1
)
py -3 -m streamlit run app.py
pause
