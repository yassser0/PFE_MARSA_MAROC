
import subprocess
import time
import os
import sys

def start():
    print("🚀 Démarrage du système de placement optimal...")
    
    # Configure environment with project root in PYTHONPATH
    env = os.environ.copy()
    project_root = os.getcwd()
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    
    # 1. Start Spark Streamer
    print("🌊 Lancement du Streamer Spark (Optimal Placement)...")
    streamer = subprocess.Popen(
        [sys.executable, "streaming/spark_streamer.py"],
        stdout=open("streamer_stdout.log", "w", encoding="utf-8"),
        stderr=open("streamer_stderr.log", "w", encoding="utf-8"),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    time.sleep(10) # Wait for Spark to initialize
    
    # 2. Start Producer
    print("📦 Lancement du Producteur de données...")
    producer = subprocess.Popen(
        [sys.executable, "streaming/producer.py", "--interval", "3"],
        stdout=open("producer_stdout.log", "w", encoding="utf-8"),
        stderr=open("producer_stderr.log", "w", encoding="utf-8"),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    print("✅ Les deux processus sont lancés.")
    print("📄 Suivez les logs : streamer_stdout.log, streamer_stderr.log, producer_stdout.log")
    
    try:
        while True:
            time.sleep(1)
            if streamer.poll() is not None:
                print("❌ Le streamer s'est arrêté de manière inattendue.")
                break
            if producer.poll() is not None:
                print("❌ Le producteur s'est arrêté de manière inattendue.")
                break
    except KeyboardInterrupt:
        print("\nStopping all...")
        streamer.terminate()
        producer.terminate()

if __name__ == "__main__":
    start()
