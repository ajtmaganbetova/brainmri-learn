import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

local = MongoClient("mongodb://localhost:27017/")
cloud = MongoClient(os.environ["MONGO_URI_CLOUD"], tlsCAFile=certifi.where())

local_db = local["brainmri_learn"]
cloud_db = cloud["brainmri_learn"]

collections = ["users", "materials", "interactions"]

try:
    local.admin.command("ping")
    cloud.admin.command("ping")

    for name in collections:
        source = local_db[name]
        destination = cloud_db[name]

        documents = list(source.find())

        if destination.count_documents({}) > 0:
            print(f"Skipping {name}: cloud collection is not empty")
            continue

        if documents:
            destination.insert_many(documents)

        # Copy non-default indexes
        for index in source.list_indexes():
            if index["name"] == "_id_":
                continue

            options = {"name": index["name"]}

            if index.get("unique"):
                options["unique"] = True

            destination.create_index(list(index["key"].items()), **options)

        print(f"{name}: migrated {len(documents)} documents")

    print("Migration completed!")

finally:
    local.close()
    cloud.close()
