echo off
TITLE Marsa Maroc Project Starter
echo 🚀 Demarrage du projet Marsa Maroc...

echo 📦 1. Lancement de MongoDB (Docker)...
docker-compose up -d

echo 🌐 2. Lancement de l'API Backend...
start powershell -NoExit -Command "python main.py api"

echo 💻 3. Lancement du Frontend React...
start powershell -NoExit -Command "cd frontend; npm run dev"

echo ✅ Tout est lance !
pause
