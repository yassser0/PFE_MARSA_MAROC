@echo off
TITLE Marsa Maroc — Big Data Stack Starter
echo ============================================================
echo   MARSA MAROC — Demarrage du Stack Complet
echo   MongoDB + HDFS + API Backend + Frontend React
echo ============================================================
echo.

echo [1/5] Demarrage de MongoDB + HDFS NameNode + DataNode (Docker)...
docker-compose up -d
timeout /t 5 /nobreak >nul

echo.
echo [2/5] Attente du NameNode HDFS (30 secondes)...
timeout /t 30 /nobreak >nul

echo.
echo [3/5] Initialisation des repertoires HDFS...
start /wait powershell -NoExit -Command "Write-Host 'Init HDFS...' -ForegroundColor Cyan; python setup_hdfs_dirs.py; Write-Host 'HDFS OK!' -ForegroundColor Green; Start-Sleep 3; exit"

echo.
echo [4/5] Lancement de l'API Backend (FastAPI)...
start powershell -NoExit -Command "cd '%~dp0'; Write-Host 'API Backend...' -ForegroundColor Cyan; python main.py api"

echo.
echo [5/5] Lancement du Frontend React (Vite)...
start powershell -NoExit -Command "cd '%~dp0frontend'; Write-Host 'Frontend React...' -ForegroundColor Green; npm run dev"

echo.
echo ============================================================
echo   Tous les services sont lances !
echo.
echo   API Backend   : http://localhost:8000/docs
echo   Frontend      : http://localhost:5173
echo   HDFS Web UI   : http://localhost:9870
echo   DataNode UI   : http://localhost:9864
echo   MongoDB       : localhost:27017
echo ============================================================
pause
