@echo off
setlocal
cd /d "%~dp0"

echo Starting Vibe-Trading backend on http://127.0.0.1:8899 ...
start "Vibe Backend 8899" /min "%~dp0.venv\Scripts\vibe-trading.exe" serve --host 127.0.0.1 --port 8899

echo Starting Auto Trade frontend on http://localhost:5899 ...
start "Vibe Frontend 5899" /min cmd /c "cd /d "%~dp0" && npm run dev --prefix frontend"

echo.
echo Open http://localhost:5899/auto-trade
endlocal