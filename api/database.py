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
    async def close_storage_connection(cls):
        """Ferme la connexion à MongoDB."""
        if cls.client:
            cls.client.close()
            print("🔌 Connexion MongoDB fermée.")

db = MongoDB()
