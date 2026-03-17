import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_mongodb():
    print("🔍 Vérification des données dans MongoDB...")
    
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    uri = f"mongodb://{host}:{port}"
    
    try:
        client = AsyncIOMotorClient(uri)
        db = client.marsa_maroc
        
        # Compter les conteneurs
        count = await db.containers.count_documents({})
        print(f"📊 Nombre total de conteneurs dans MongoDB : {count}")
        
        if count > 0:
            print("\n📋 Dernières entrées :")
            async for container in db.containers.find().sort("imported_at", -1).limit(5):
                print(f" - ID: {container.get('id')}, Slot: {container.get('slot')}, Importé le: {container.get('imported_at')}")
        else:
            print("❌ Aucun conteneur trouvé. Avez-vous effectué un import CSV ?")
            
        client.close()
    except Exception as e:
        print(f"❌ Erreur lors de la vérification : {e}")

if __name__ == "__main__":
    asyncio.run(verify_mongodb())
