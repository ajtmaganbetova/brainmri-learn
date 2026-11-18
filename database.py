from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)

db = client["brainmri_learn"]

users_collection = db["users"]
materials_collection = db["materials"]
interactions_collection = db["interactions"]

client.admin.command("ping")
print("Successfully connected to local MongoDB!")
