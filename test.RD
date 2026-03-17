1.# Entrer dans le shell mongosh du container
docker exec -it marsa_maroc_mongodb mongosh
use marsa_maroc
db.containers.find().limit(5)


