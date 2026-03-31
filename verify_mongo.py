from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
db = client.marsa_maroc
total = db.containers.count_documents({})
streaming = db.containers.count_documents({"found_by": "SparkStreaming"})
print(f"Total containers: {total}")
print(f"Streaming placements: {streaming}")
if streaming > 0:
    last = db.containers.find_one({"found_by": "SparkStreaming"}, sort=[("_id", -1)])
    print(f"Last streaming placement: {last.get('id')} at {last.get('slot')}")
