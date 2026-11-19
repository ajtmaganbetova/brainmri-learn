import os
import certifi

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.environ["MONGO_URI"]

client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000)

db = client["brainmri_learn"]

users_collection = db["users"]
materials_collection = db["materials"]
interactions_collection = db["interactions"]
