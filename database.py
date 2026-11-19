import os
import certifi

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000)

db = client["brainmri_learn"]

users_collection = db["users"]
materials_collection = db["materials"]
interactions_collection = db["interactions"]
