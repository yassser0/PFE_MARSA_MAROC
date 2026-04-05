"""
api/database.py
===============
Gestion de la connexion à MongoDB pour le projet PFE Marsa Maroc.
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_to_storage(cls):
        """Initialise la connexion à MongoDB."""
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        try:
            cls.client = AsyncIOMotorClient(mongo_uri)
            cls.db = cls.client.marsa_maroc
            
            # Création des index d'optimisation
            import pymongo
            await cls.db.containers.create_index([("id", pymongo.ASCENDING)], unique=True)
            await cls.db.containers.create_index([("slot", pymongo.ASCENDING)])
            
            # Test de connexion
            await cls.client.admin.command('ping')
            print("✅ Connecté à MongoDB avec succès.")
        except Exception as e:
            print(f"❌ Erreur de connexion MongoDB : {e}")

    @classmethod
    async def save_container(cls, container_data: dict):
        """Sauvegarde ou met à jour un conteneur dans MongoDB."""
        if cls.db is None:
            return False
            
        from datetime import datetime
        if "imported_at" not in container_data:
            container_data["imported_at"] = datetime.now().isoformat()
            
        try:
            await cls.db.containers.update_one(
                {"id": container_data["id"]},
                {"$set": container_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde MongoDB : {e}")
            return False

    @classmethod
    async def save_containers(cls, containers_data: list[dict]):
        """Sauvegarde ou met à jour une liste de conteneurs en masse (bulk_write) dans MongoDB."""
        if cls.db is None or not containers_data:
            return False
            
        from datetime import datetime
        now_str = datetime.now().isoformat()
        for c in containers_data:
            if "imported_at" not in c:
                c["imported_at"] = now_str
                
        try:
            from pymongo import UpdateOne
            operations = [
                UpdateOne({"id": c["id"]}, {"$set": c}, upsert=True)
                for c in containers_data
            ]
            await cls.db.containers.bulk_write(operations)
            print(f"✅ {len(containers_data)} conteneurs ont été bien sauvegardés dans MongoDB.")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde en masse MongoDB : {e}")
            return False

    @classmethod
    async def get_all_containers(cls):
        """Récupère tous les conteneurs avec un slot assigné."""
        if cls.db is None:
            return []
        try:
            cursor = cls.db.containers.find({"slot": {"$exists": True}})
            return await cursor.to_list(length=5000)
        except Exception as e:
            print(f"❌ Erreur lecture MongoDB : {e}")
            return []

    @classmethod
    async def clear_all_containers(cls):
        """Supprime tous les conteneurs de la base de données."""
        if cls.db is None:
            return False
        try:
            await cls.db.containers.delete_many({})
            print("🧹 Tous les conteneurs ont été supprimés de MongoDB.")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression MongoDB : {e}")
            return False

    @classmethod
    async def close_storage_connection(cls):
        """Ferme la connexion à MongoDB."""
        if cls.client:
            cls.client.close()
            print("🔌 Connexion MongoDB fermée.")

db = MongoDB()
