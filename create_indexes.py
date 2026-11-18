from pymongo import ASCENDING, DESCENDING
from database import users_collection, materials_collection, interactions_collection

# 1. Users: fast login lookup
users_collection.create_index([("email", ASCENDING)], unique=True)

# 2. Materials: category filtering
materials_collection.create_index([("category", ASCENDING)])

# 3. Materials: title lookup
materials_collection.create_index([("title", ASCENDING)])

# 4. Interactions: user history
interactions_collection.create_index(
    [("user_id", ASCENDING), ("timestamp", DESCENDING)]
)

# 5. Interactions: material ratings
interactions_collection.create_index([("material_id", ASCENDING), ("type", ASCENDING)])

# 6. Interactions: find a user's rating
interactions_collection.create_index(
    [("user_id", ASCENDING), ("material_id", ASCENDING), ("type", ASCENDING)]
)

print("MongoDB indexes created")

for collection in [users_collection, materials_collection, interactions_collection]:
    print(f"\nCollection: {collection.name}")

    for index in collection.list_indexes():
        print("-", index["name"])
