@echo off
cd /d "%~dp0"
echo Memulai Midnight Cowork (FastAPI Server)...
start "" pythonw main.py
echo Menunggu inisialisasi Open Interpreter (sekitar 6 detik)...
timeout /t 6 /nobreak >nul
start http://127.0.0.1:8000
exit
