import csv
import time
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

from database import db, users_collection, materials_collection, interactions_collection

OUTPUT = Path("performance_results")
OUTPUT.mkdir(exist_ok=True)

REPEATS = 30

# Get real IDs from the current database
interaction = interactions_collection.find_one({"type": "rating"})

material = materials_collection.find_one({"category": "Glioma"})

if not interaction or not material:
    raise RuntimeError("Test data missing. Run seed.py first.")

user_id = interaction["user_id"]
rated_material_id = interaction["material_id"]

# Each test compares an identical query
tests = [
    {
        "name": "Category Search",
        "collection": materials_collection,
        "filter": {"category": "Glioma"},
        "sort": None,
        "index": "category_1",
    },
    {
        "name": "User History",
        "collection": interactions_collection,
        "filter": {"user_id": user_id},
        "sort": [("timestamp", -1)],
        "index": "user_id_1_timestamp_-1",
    },
    {
        "name": "Material Ratings",
        "collection": interactions_collection,
        "filter": {"material_id": rated_material_id, "type": "rating"},
        "sort": None,
        "index": "material_id_1_type_1",
    },
]


def execute_query(test, hint):
    cursor = test["collection"].find(test["filter"]).hint(hint)

    if test["sort"]:
        cursor = cursor.sort(test["sort"])

    return list(cursor)


def get_explain(test, hint):
    command = {"find": test["collection"].name, "filter": test["filter"], "hint": hint}

    if test["sort"]:
        command["sort"] = dict(test["sort"])

    return db.command("explain", command, verbosity="executionStats")


def get_plan_stages(node):
    stages = []

    if isinstance(node, dict):
        if "stage" in node:
            stages.append(node["stage"])

        for value in node.values():
            stages.extend(get_plan_stages(value))

    elif isinstance(node, list):
        for value in node:
            stages.extend(get_plan_stages(value))

    return stages


results = []

for test in tests:
    print(f"\nTesting: {test['name']}")

    for mode, hint in [
        ("Without Index", {"$natural": 1}),
        ("With Index", test["index"]),
    ]:

        # Warm-up query
        execute_query(test, hint)

        timings = []

        for _ in range(REPEATS):
            start = time.perf_counter()

            documents = execute_query(test, hint)

            elapsed = (time.perf_counter() - start) * 1000

            timings.append(elapsed)

        explain = get_explain(test, hint)
        stats = explain["executionStats"]

        stages = get_plan_stages(explain["queryPlanner"]["winningPlan"])

        result = {
            "query": test["name"],
            "mode": mode,
            "avg_time_ms": round(statistics.mean(timings), 4),
            "median_time_ms": round(statistics.median(timings), 4),
            "docs_examined": stats["totalDocsExamined"],
            "keys_examined": stats["totalKeysExamined"],
            "execution_time_ms": stats["executionTimeMillis"],
            "returned_documents": len(documents),
            "plan": ", ".join(sorted(set(stages))),
        }

        results.append(result)

        print(
            f"{mode}: "
            f"{result['avg_time_ms']:.4f} ms | "
            f"Docs: {result['docs_examined']} | "
            f"Keys: {result['keys_examined']} | "
            f"Plan: {result['plan']}"
        )


# Save CSV
csv_path = OUTPUT / "query_performance.csv"

with open(csv_path, "w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())

    writer.writeheader()
    writer.writerows(results)

print(f"\nCSV saved: {csv_path}")


# Create comparison chart
names = [t["name"] for t in tests]

without = [
    next(
        r["avg_time_ms"]
        for r in results
        if r["query"] == name and r["mode"] == "Without Index"
    )
    for name in names
]

with_index = [
    next(
        r["avg_time_ms"]
        for r in results
        if r["query"] == name and r["mode"] == "With Index"
    )
    for name in names
]

x = range(len(names))
width = 0.35

fig, ax = plt.subplots(figsize=(9, 5))

ax.bar([i - width / 2 for i in x], without, width, label="Without Index")

ax.bar([i + width / 2 for i in x], with_index, width, label="With Index")

ax.set_xticks(list(x))
ax.set_xticklabels(names)

ax.set_ylabel("Average query time (ms)")
ax.set_title("MongoDB Query Performance Comparison")
ax.legend()

plt.tight_layout()

chart_path = OUTPUT / "query_performance.png"
plt.savefig(chart_path, dpi=200)
plt.show()

print(f"Chart saved: {chart_path}")
print("\nPerformance testing completed!")
