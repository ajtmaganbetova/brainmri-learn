import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

client = None

try:
    client = MongoClient(
        os.environ["MONGO_URI_CLOUD"],
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
    )

    client.admin.command("ping")
    print("Successfully connected to MongoDB Atlas!")

    db = client["brainmri_learn"]

    for name in ["users", "materials", "interactions"]:
        count = db[name].count_documents({})
        print(f"{name}: {count}")

except PyMongoError as error:
    print("MongoDB connection failed:")
    print(type(error).__name__)
    print(str(error))

finally:
    if client is not None:
        client.close()
