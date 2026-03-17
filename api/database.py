import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None
    
    @classmethod
    async def connect_to_storage(cls):
        """Initialise la connexion à MongoDB."""
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        uri = f"mongodb://{host}:{port}"
        
        print(f"🔌 Tentative de connexion à MongoDB : {uri}")
        try:
            cls.client = AsyncIOMotorClient(uri)
            cls.db = cls.client.marsa_maroc
            # Vérification de la connexion
            await cls.client.admin.command('ping')
            print("✅ Connecté à MongoDB avec succès.")
        except Exception as e:
            print(f"❌ Erreur de connexion MongoDB : {e}")

    @classmethod
    async def close_storage_connection(cls):
        """Ferme la connexion à MongoDB."""
        if cls.client:
            cls.client.close()
            print("🛑 Connexion MongoDB fermée.")

    @classmethod
    async def save_containers(cls, containers_data: list):
        """Enregistre un lot de conteneurs dans la collection 'containers'."""
        if cls.db is None:
            print("⚠️ MongoDB non connecté. Données non sauvegardées.")
            return False
            
        try:
            timestamp = datetime.now()
            # On ajoute un timestamp à chaque entrée pour le suivi
            for item in containers_data:
                item["imported_at"] = timestamp
                
            result = await cls.db.containers.insert_many(containers_data)
            print(f"💾 {len(result.inserted_ids)} conteneurs sauvegardés dans MongoDB.")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde MongoDB : {e}")
            return False

db = MongoDB()
