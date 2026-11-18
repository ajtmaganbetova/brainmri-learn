from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import Field
from pymongo.errors import DuplicateKeyError
import jwt
from datetime import datetime, timezone
from typing import Literal
from pydantic import model_validator
from database import users_collection
from auth import hash_password, verify_password, create_access_token
from database import materials_collection, interactions_collection
from recommender import get_recommendations

app = FastAPI(title="BrainMRI Learn API")

class Material(BaseModel):
    title: str
    description: str
    category: str
    difficulty: str

def serialize_material(material):
    material["_id"] = str(material["_id"])
    return material

@app.get("/")
def home():
    return {"message": "Welcome to BrainMRI Learn!"}

# READ: Get all materials
@app.get("/materials")
def get_materials():
    materials = materials_collection.find()
    return [serialize_material(m) for m in materials]


# SEARCH: Find materials by category or title
@app.get("/materials/search")
def search_materials(category: str = None, title: str = None):
    query = {}

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if title:
        query["title"] = {"$regex": title, "$options": "i"}

    materials = materials_collection.find(query)
    return [serialize_material(m) for m in materials]


# READ: Get one material
@app.get("/materials/{material_id}")
def get_material(material_id: str):
    try:
        obj_id = ObjectId(material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    material = materials_collection.find_one({"_id": obj_id})

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return serialize_material(material)


# CREATE: Add material
@app.post("/materials", status_code=201)
def create_material(material: Material):
    result = materials_collection.insert_one(material.model_dump())

    return {"message": "Material created", "id": str(result.inserted_id)}


# UPDATE: Edit material
@app.put("/materials/{material_id}")
def update_material(material_id: str, material: Material):
    try:
        obj_id = ObjectId(material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    result = materials_collection.update_one(
        {"_id": obj_id}, {"$set": material.model_dump()}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Material not found")

    return {"message": "Material updated"}


# DELETE: Remove material
@app.delete("/materials/{material_id}")
def delete_material(material_id: str):
    try:
        obj_id = ObjectId(material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    result = materials_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Material not found")

    return {"message": "Material deleted"}


# USER AUTHENTICATION

security = HTTPBearer()

# Prevent duplicate emails
users_collection.create_index("email", unique=True)


class UserRegister(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


# REGISTER
@app.post("/register", status_code=201)
def register(user: UserRegister):
    email = user.email.strip().lower()

    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = {
        "name": user.name,
        "email": email,
        "password_hash": hash_password(user.password),
        "interests": [],
    }

    try:
        result = users_collection.insert_one(new_user)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
    }


# LOGIN
@app.post("/login")
def login(user: UserLogin):
    email = user.email.strip().lower()

    db_user = users_collection.find_one({"email": email})

    if not db_user or not db_user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(db_user["_id"]))

    return {"access_token": token, "token_type": "bearer"}


# GET CURRENT USER PROFILE
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, __import__("auth").SECRET_KEY, algorithms=["HS256"]
        )
        user_id = payload["sub"]
        db_user = users_collection.find_one({"_id": ObjectId(user_id)})

    except (jwt.PyJWTError, KeyError, InvalidId):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    return db_user


@app.get("/users/me")
def get_profile(user=Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "interests": user.get("interests", []),
    }


# USER INTERACTIONS & HISTORY


class Interaction(BaseModel):
    material_id: str
    type: Literal["view", "rating"]
    rating: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def check_rating(self):
        if self.type == "rating" and self.rating is None:
            raise ValueError("Rating is required")
        if self.type == "view" and self.rating is not None:
            raise ValueError("Views cannot have ratings")
        return self


# RECORD INTERACTION
@app.post("/interactions", status_code=201)
def record_interaction(interaction: Interaction, user=Depends(get_current_user)):
    try:
        material_id = ObjectId(interaction.material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid material ID")

    material = materials_collection.find_one({"_id": material_id})

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    data = {
        "user_id": str(user["_id"]),
        "material_id": str(material_id),
        "type": interaction.type,
        "rating": interaction.rating,
        "timestamp": datetime.now(timezone.utc),
    }

    if interaction.type == "rating":
        # One current rating per user and material
        interactions_collection.update_one(
            {
                "user_id": str(user["_id"]),
                "material_id": str(material_id),
                "type": "rating",
            },
            {"$set": data},
            upsert=True,
        )
    else:
        interactions_collection.insert_one(data)

    return {"message": "Interaction recorded successfully"}


# GET USER HISTORY
@app.get("/users/me/history")
def get_user_history(user=Depends(get_current_user)):
    interactions = (
        interactions_collection.find({"user_id": str(user["_id"])})
        .sort("timestamp", -1)
        .limit(100)
    )

    history = []

    for interaction in interactions:
        material = materials_collection.find_one(
            {"_id": ObjectId(interaction["material_id"])}
        )

        history.append(
            {
                "id": str(interaction["_id"]),
                "material_title": (
                    material["title"] if material else "Deleted material"
                ),
                "type": interaction["type"],
                "rating": interaction.get("rating"),
                "timestamp": interaction["timestamp"],
            }
        )

    return history


# GET MATERIAL RATING STATISTICS
@app.get("/materials/{material_id}/ratings")
def get_material_ratings(material_id: str):
    try:
        obj_id = ObjectId(material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid material ID")

    if not materials_collection.find_one({"_id": obj_id}):
        raise HTTPException(status_code=404, detail="Material not found")

    pipeline = [
        {"$match": {"material_id": str(obj_id), "type": "rating"}},
        {
            "$group": {
                "_id": None,
                "average_rating": {"$avg": "$rating"},
                "total_ratings": {"$sum": 1},
            }
        },
    ]

    results = list(interactions_collection.aggregate(pipeline))

    if not results:
        return {"average_rating": None, "total_ratings": 0}

    return {
        "average_rating": round(results[0]["average_rating"], 2),
        "total_ratings": results[0]["total_ratings"],
    }

# PERSONALIZED RECOMMENDATIONS
@app.get("/recommendations/me")
def recommend_for_current_user(limit: int = 5, user=Depends(get_current_user)):
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")

    recommendations = get_recommendations(user_id=str(user["_id"]), top_n=limit)

    return {
        "user_id": str(user["_id"]),
        "total": len(recommendations),
        "recommendations": recommendations,
    }
