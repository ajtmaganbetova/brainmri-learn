import time
import statistics
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

output = Path("performance_results")
output.mkdir(exist_ok=True)

rng = np.random.default_rng(42)

results = []

REPEATS = 10

# Increase both ratings and number of materials a bit
test_configs = [
    {"ratings": 1000, "items": 30},
    {"ratings": 5000, "items": 100},
    {"ratings": 10000, "items": 200},
]

for config in test_configs:
    n_ratings = config["ratings"]
    n_items = config["items"]
    n_users = n_ratings // 10

    timings = []

    for _ in range(REPEATS):
        rows = []

        for user in range(n_users):
            items = rng.choice(n_items, size=min(10, n_items), replace=False)

            for item in items:
                rows.append(
                    {
                        "user_id": f"user_{user}",
                        "material_id": f"material_{item}",
                        "rating": int(rng.integers(1, 6)),
                    }
                )

        df = pd.DataFrame(rows)

        start = time.perf_counter()

        matrix = df.pivot(
            index="user_id", columns="material_id", values="rating"
        ).fillna(0)

        similarity = cosine_similarity(matrix.T)

        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    avg_time = statistics.mean(timings)
    median_time = statistics.median(timings)

    results.append(
        {
            "ratings": n_ratings,
            "users": n_users,
            "materials": n_items,
            "avg_time_ms": avg_time,
            "median_time_ms": median_time,
        }
    )

    print(
        f"{n_ratings} ratings, {n_items} materials -> "
        f"avg: {avg_time:.3f} ms, median: {median_time:.3f} ms"
    )

results_df = pd.DataFrame(results)
results_df.to_csv(output / "scalability_results.csv", index=False)

plt.figure(figsize=(8, 5))
plt.plot(results_df["ratings"], results_df["avg_time_ms"], marker="o")
plt.xlabel("Number of ratings")
plt.ylabel("Average execution time (ms)")
plt.title("Recommendation Algorithm Scalability")
plt.tight_layout()
plt.savefig(output / "scalability_results.png", dpi=200)
plt.show()

print("\nImproved scalability testing completed!") 