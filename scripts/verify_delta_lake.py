import os
from pyspark.sql import SparkSession
from pipeline.etl_pipeline import get_pipeline

def verify():
    print("🔍 Démarrage de la vérification Delta Lake...")
    pipeline = get_pipeline()
    spark = pipeline.spark
    
    # Check Delta config
    extensions = spark.conf.get("spark.sql.extensions", "")
    if "DeltaSparkSessionExtension" in extensions:
        print("✅ Extensions Delta Lake détectées.")
    else:
        print("❌ Extensions Delta Lake manquantes !")
        
    # Run a dummy ETL to verify partitioning (using local mode for verification)
    from pipeline.silver_layer_spark import SilverLayerSpark
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
    
    schema = StructType([
        StructField("id", StringType()),
        StructField("weight", DoubleType()),
        StructField("size", IntegerType()),
        StructField("departure_time", StringType()),
        StructField("type", StringType())
    ])
    
    data = [
        ("CNTR001", 10.0, 20, "2026-04-01T10:00:00", "import"),
        ("CNTR002", 15.0, 40, "2026-04-01T12:00:00", "export"),
        ("CNTR003", 20.0, 20, "2026-04-02T14:00:00", "import")
    ]
    
    df_raw = spark.createDataFrame(data, schema)
    silver = SilverLayerSpark(spark, storage_mode="local")
    df_clean, report = silver.process(df_raw)
    
    output_path = report["output_path"].replace("file:///", "")
    if os.name == 'nt':
        output_path = output_path.replace("/", "\\")
        
    print(f"📁 Vérification du dossier de sortie : {output_path}")
    
    if os.path.exists(os.path.join(output_path, "_delta_log")):
        print("✅ Log Delta Lake (_delta_log) trouvé.")
    else:
        print("❌ Log Delta Lake manquant !")
        
    # Check partitions
    types = ["type=import", "type=export"]
    for t in types:
        if any(t in d for d in os.listdir(output_path)):
            print(f"✅ Partition {t} trouvée.")
        else:
            print(f"❌ Partition {t} manquante !")

if __name__ == "__main__":
    verify()
