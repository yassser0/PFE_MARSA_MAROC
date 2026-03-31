
import os
import json
from datetime import datetime
try:
    from pyspark.sql import SparkSession
    print("✅ PySpark imported")
    from pymongo import MongoClient
    print("✅ PyMongo imported")
    from models.yard import Yard
    print("✅ Yard model imported")
    from models.container import Container, ContainerType
    print("✅ Container model imported")
    from services.optimizer import find_best_slot
    print("✅ Optimizer service imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Error during imports: {e}")
