import random
from datetime import datetime, timezone

from database import users_collection, materials_collection, interactions_collection

random.seed(42)

categories = {
    "Glioma": [
        "Introduction to Glioma MRI",
        "Glioma Classification Basics",
        "Glioma MRI Characteristics",
        "Low-Grade vs High-Grade Gliomas",
        "Glioblastoma MRI Features",
        "Glioma Detection Methods",
    ],
    "Meningioma": [
        "Introduction to Meningioma",
        "Meningioma MRI Features",
        "Meningioma Classification",
        "Meningioma Imaging Basics",
        "Meningioma Detection",
        "Meningioma Case Studies",
    ],
    "Pituitary Tumor": [
        "Introduction to Pituitary Tumors",
        "Pituitary MRI Basics",
        "Pituitary Adenoma Features",
        "Pituitary Tumor Classification",
        "Pituitary MRI Case Studies",
        "Pituitary Tumor Detection",
    ],
    "Explainable AI": [
        "Introduction to Explainable AI",
        "Grad-CAM Visualization",
        "AI Heatmaps in MRI",
        "Interpreting AI Predictions",
        "Explainability in Medical Imaging",
        "Visualization of Tumor Classification",
    ],
    "MRI Preprocessing": [
        "Introduction to MRI Preprocessing",
        "MRI Image Normalization",
        "Brain MRI Segmentation",
        "MRI Noise Reduction",
        "MRI Data Augmentation",
        "MRI Image Registration",
    ],
}

# 1. Create 30 materials
material_ids = []
material_categories = {}

for category, titles in categories.items():
    for title in titles:
        key = f"demo_material:{title}"

        existing = materials_collection.find_one({"seed_key": key})

        if existing:
            material_id = existing["_id"]
        else:
            result = materials_collection.insert_one(
                {
                    "title": title,
                    "description": f"Learning resource about {title.lower()}",
                    "category": category,
                    "difficulty": random.choice(
                        ["Beginner", "Intermediate", "Advanced"]
                    ),
                    "is_test_data": True,
                    "seed_key": key,
                }
            )
            material_id = result.inserted_id

        material_ids.append(str(material_id))
        material_categories[str(material_id)] = category

print("30 test materials prepared")

# 2. Create 100 synthetic users
user_ids = []
user_preferences = {}

category_names = list(categories.keys())

for i in range(1, 101):
    email = f"demo_student_{i}@example.com"
    favorite = random.choice(category_names)

    existing = users_collection.find_one({"email": email})

    if existing:
        user_id = existing["_id"]
    else:
        result = users_collection.insert_one(
            {
                "name": f"Demo Student {i}",
                "email": email,
                "interests": [favorite],
                "is_test_data": True,
            }
        )
        user_id = result.inserted_id

    user_ids.append(str(user_id))
    user_preferences[str(user_id)] = favorite

print("100 test users prepared")

# 3. Create 1000 ratings
# Each user rates 10 different materials.
created = 0

for user_id in user_ids:
    favorite = user_preferences[user_id]
    selected = random.sample(material_ids, 10)

    for material_id in selected:
        # Users tend to prefer their favorite category.
        if material_categories[material_id] == favorite:
            rating = random.choice([4, 4, 5, 5, 5])
        else:
            rating = random.randint(1, 5)

        result = interactions_collection.update_one(
            {"user_id": user_id, "material_id": material_id, "type": "rating"},
            {
                "$setOnInsert": {
                    "rating": rating,
                    "timestamp": datetime.now(timezone.utc),
                    "is_test_data": True,
                }
            },
            upsert=True,
        )

        if result.upserted_id is not None:
            created += 1

print(f"{created} new ratings created")

print("Database seeding completed!")
