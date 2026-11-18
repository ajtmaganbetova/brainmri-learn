import numpy as np
import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity

from database import materials_collection, interactions_collection

#item-based collaborative filtering
def get_recommendations(user_id, top_n=5):

    # 1. Load all ratings from MongoDB
    ratings = list(
        interactions_collection.find(
            {"type": "rating", "rating": {"$gte": 1, "$lte": 5}},
            {"_id": 0, "user_id": 1, "material_id": 1, "rating": 1},
        )
    )

    if not ratings:
        return []

    # 2. Create a user-item rating matrix
    df = pd.DataFrame(ratings)

    df = df.drop_duplicates(subset=["user_id", "material_id"], keep="last")

    matrix = df.pivot(index="user_id", columns="material_id", values="rating").fillna(0)

    # 3. Calculate item-item similarity
    similarity = cosine_similarity(matrix.T)

    similarity_df = pd.DataFrame(
        similarity, index=matrix.columns, columns=matrix.columns
    )

    # 4. Retrieve the current user's ratings
    if user_id in matrix.index:
        user_ratings = matrix.loc[user_id]
        rated_items = user_ratings[user_ratings > 0]
    else:
        rated_items = pd.Series(dtype=float)

    scores = {}

    # 5. Predict scores for unrated materials
    if len(rated_items) > 0:
        for material_id in matrix.columns:

            if material_id in rated_items.index:
                continue

            item_similarities = similarity_df.loc[material_id, rated_items.index].copy()

            item_similarities = item_similarities[item_similarities > 0]

            if item_similarities.empty:
                continue

            weighted_score = (
                item_similarities * rated_items[item_similarities.index]
            ).sum()

            total_similarity = item_similarities.sum()

            scores[material_id] = float(weighted_score / total_similarity)

    # 6. Cold-start fallback: popular materials
    popularity = df.groupby("material_id")["rating"].agg(["mean", "count"])

    popularity["score"] = (
        popularity["mean"] * popularity["count"] / (popularity["count"] + 5)
    )

    # 7. Rank and return recommendations
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    seen = set(rated_items.index)
    selected = []

    for material_id, score in ranked:
        if len(selected) >= top_n:
            break

        selected.append((material_id, score, "collaborative_filtering"))
        seen.add(material_id)

    # Fill remaining slots with popular materials
    popular_ids = popularity.sort_values("score", ascending=False).index

    for material_id in popular_ids:
        if len(selected) >= top_n:
            break

        if material_id in seen:
            continue

        selected.append(
            (
                material_id,
                float(popularity.loc[material_id, "mean"]),
                "popular_fallback",
            )
        )
        seen.add(material_id)

    results = []

    from bson import ObjectId

    for material_id, score, method in selected:
        material = materials_collection.find_one({"_id": ObjectId(material_id)})

        if not material:
            continue

        results.append(
            {
                "material_id": str(material["_id"]),
                "title": material["title"],
                "description": material.get("description", ""),
                "category": material.get("category", ""),
                "difficulty": material.get("difficulty", ""),
                "predicted_score": round(score, 2),
                "method": method,
            }
        )

    return results
