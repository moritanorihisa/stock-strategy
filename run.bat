@echo off
cd /d "%~dp0"
echo 必要なライブラリをインストールしています...
pip install -r requirements.txt
echo.
echo Streamlitアプリを起動しています...
streamlit run app.py
pause
