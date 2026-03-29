"""
setup_hdfs_dirs.py
==================
Script d'initialisation des repertoires HDFS pour la pipeline Marsa Maroc.

Cree les dossiers suivants dans HDFS :
  /marsa_maroc/bronze/
  /marsa_maroc/silver/
  /marsa_maroc/gold/
  /marsa_maroc/raw/

Usage :
  python setup_hdfs_dirs.py

Prerequis :
  - HDFS Docker en cours d'execution (docker-compose up -d namenode datanode)
  - PySpark installe
"""

import time
import socket
import sys

HDFS_HOST = "localhost"
HDFS_PORT = 9000
HDFS_URL  = f"hdfs://{HDFS_HOST}:{HDFS_PORT}"

HDFS_DIRS = [
    "/marsa_maroc",
    "/marsa_maroc/bronze",
    "/marsa_maroc/silver",
    "/marsa_maroc/gold",
    "/marsa_maroc/raw",
]


def wait_for_hdfs(host: str, port: int, timeout: int = 60) -> bool:
    """Attend que HDFS soit disponible (max timeout secondes)."""
    print(f"Attente de HDFS {host}:{port}...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
            print(" OK!")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            print(".", end="", flush=True)
            time.sleep(2)
    print(" TIMEOUT!")
    return False


def create_hdfs_dirs():
    """Cree les repertoires HDFS via PySpark."""
    import os
    os.environ["HADOOP_USER_NAME"] = "root"

    print("\n== Initialisation des repertoires HDFS Marsa Maroc ==")
    print(f"   NameNode : {HDFS_URL}")

    if not wait_for_hdfs(HDFS_HOST, HDFS_PORT, timeout=60):
        print("\nERREUR : HDFS inaccessible.")
        print("Verifiez que le cluster est demarre : docker-compose up -d namenode datanode")
        sys.exit(1)

    # Patience supplementaire pour que le NameNode sorte du Safe Mode
    print("Attente du NameNode (sortie du Safe Mode)...")
    time.sleep(15)

    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .master("local[1]")
        .appName("HDFS_Setup")
        .config("spark.hadoop.fs.defaultFS", HDFS_URL)
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    # Utiliser l'API Hadoop FileSystem via Java Gateway
    sc = spark.sparkContext
    hadoop_conf = sc._jsc.hadoopConfiguration()
    fs = sc._jvm.org.apache.hadoop.fs.FileSystem.get(
        sc._jvm.java.net.URI(HDFS_URL),
        hadoop_conf
    )

    created = []
    skipped = []

    for hdfs_dir in HDFS_DIRS:
        path = sc._jvm.org.apache.hadoop.fs.Path(hdfs_dir)
        if not fs.exists(path):
            fs.mkdirs(path)
            created.append(hdfs_dir)
            print(f"  [CREE]  {hdfs_dir}")
        else:
            skipped.append(hdfs_dir)
            print(f"  [EXISTE] {hdfs_dir}")

    # Verifier les permissions
    for hdfs_dir in HDFS_DIRS:
        path = sc._jvm.org.apache.hadoop.fs.Path(hdfs_dir)
        status = fs.getFileStatus(path)
        print(f"  [OK] {hdfs_dir}  (permissions: {status.getPermission()})")

    spark.stop()

    print("\n== Resultat ==")
    print(f"   Crees   : {len(created)} dossiers")
    print(f"   Existants: {len(skipped)} dossiers")
    print(f"\nHDFS accessible sur : http://localhost:9870")
    print("Repertoires Marsa Maroc crees avec succes !")


if __name__ == "__main__":
    create_hdfs_dirs()
