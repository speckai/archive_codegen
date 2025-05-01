import json
import os
import statistics

# Specify the model names exactly as printed in the summary file names.
# For example, if your benchmark script dumps files like:
# summaries_Model.CLAUDE_SONNET.json, summaries_Model.GEMINI_1_5_FLASH_8B.json, etc.
MODELS = [
    "Model.CLAUDE_SONNET",
    "Model.GPT_4o",
    "Model.GPT_4o_MINI",
    "Model.GEMINI_2_0_FLASH",
    "Model.GEMINI_2_0_FLASH_LITE",
    "Model.GEMINI_1_5_FLASH",
    "Model.GEMINI_1_5_FLASH_8B",
    "Model.DEEPSEEK_R1_DISTILL_LLAMA_70B",
    "Model.LLAMA_3_1_8B_INSTANT",
    "Model.LLAMA_3_3_70B_VERSATILE",
]

# Model to test against
BASE_MODEL = "Model.CLAUDE_SONNET"

SUMMARY_FILENAME_TEMPLATE = "summaries_{}.json"


def load_model_summaries(model_name):
    """
    Loads a summary JSON file for a given model.
    The file should contain a list of runs; each run is a dictionary with a "summaries" list.
    For each response summary (with keys: file_path, id, score), we group scores per id.
    Returns:
       - stats_by_id: dict mapping id -> { count, mean, median, min, max, stdev }
       - file_path_by_id: dict mapping id -> file_path (from the first occurrence)
    """
    filename = SUMMARY_FILENAME_TEMPLATE.format(model_name)
    if not os.path.exists(filename):
        print(f"Summary file for model {model_name} not found: {filename}")
        return {}, {}
    with open(filename, "r") as f:
        runs = json.load(f)

    scores_by_id = {}
    file_path_by_id = {}

    for run in runs:
        for summary in run.get("summaries", []):
            id_ = summary.get("id")
            if id_ is None:
                continue
            score = summary.get("score")
            file_path = summary.get("file_path", "N/A")
            scores_by_id.setdefault(id_, []).append(score)
            # Save the file_path (from the first occurrence) for reference.
            if id_ not in file_path_by_id:
                file_path_by_id[id_] = file_path

    stats_by_id = {}
    for id_, scores in scores_by_id.items():
        count = len(scores)
        mean_val = statistics.mean(scores)
        median_val = statistics.median(scores)
        min_val = min(scores)
        max_val = max(scores)
        try:
            stdev_val = statistics.stdev(scores) if count > 1 else 0
        except Exception:
            stdev_val = 0
        stats_by_id[id_] = {
            "count": count,
            "mean": mean_val,
            "median": median_val,
            "min": min_val,
            "max": max_val,
            "stdev": stdev_val,
        }
    return stats_by_id, file_path_by_id


def main():
    print(f"Loading summaries for base model: {BASE_MODEL}")
    base_stats, base_file_paths = load_model_summaries(BASE_MODEL)

    # Load stats for all the other models.
    other_models = [model for model in MODELS if model != BASE_MODEL]
    other_stats_dict = {}
    for model in other_models:
        print(f"Loading summaries for {model} ...")
        stats, _ = load_model_summaries(model)
        other_stats_dict[model] = stats

    full_comparison = []

    overall_deviations = {model: [] for model in other_models}

    # For each result, print a nicely formatted section.
    for id_ in sorted(base_stats.keys()):
        base = base_stats[id_]
        file_path = base_file_paths.get(id_, "N/A")
        header = f"Result: {id_} | File: {file_path}"
        print("\n" + "=" * len(header))
        print(header)
        print("=" * len(header))
        # Print base model stats
        print(
            f"Base ({BASE_MODEL}): Count={base['count']:>2}, Mean={base['mean']:6.2f}, "
            f"Median={base['median']:6.2f}, Min={base['min']:6.2f}, Max={base['max']:6.2f}, "
            f"StDev={base['stdev']:6.2f}"
        )

        # Build ranking for other models for this id.
        ranking = []
        for model in other_models:
            stats = other_stats_dict.get(model, {}).get(id_)
            if stats:
                diff = stats["mean"] - base["mean"]
                # Compute relative performance percentage: base is 100%
                # (if base mean is 0, set performance to None)
                if base["mean"]:
                    performance = (stats["mean"] / base["mean"]) * 100
                else:
                    performance = None
                ranking.append((model, stats, diff, performance))
                # Save deviation for overall ranking.
                overall_deviations[model].append(abs(diff))
        ranking.sort(key=lambda tup: abs(tup[2]))  # sort by absolute difference

        # Print header for ranking table with the new "Perf (%)" column.
        print("\nRanked comparisons:")
        print(
            f"{'Rank':<5}{'Model':<35}{'Mean':>8}{'Diff':>10}{'Perf (%)':>10}"
            f"{'Count':>8}{'Median':>10}{'Min':>8}{'Max':>8}{'StDev':>10}"
        )
        print("-" * 110)
        for rank, (model, stats, diff, performance) in enumerate(ranking, start=1):
            perf_str = (
                f"{performance:10.2f}" if performance is not None else "    N/A   "
            )
            print(
                f"{rank:<5}{model:<35}{stats['mean']:8.2f}{diff:10.2f}"
                f"{perf_str}{stats['count']:8}{stats['median']:10.2f}"
                f"{stats['min']:8.2f}{stats['max']:8.2f}{stats['stdev']:10.2f}"
            )
        print("=" * 100)

        # Save the details for JSON dumping.
        result_entry = {
            "id": id_,
            "file_path": file_path,
            "base": base,
            "comparisons": {
                model: {
                    "stats": other_stats_dict.get(model, {}).get(id_),
                    "diff": (
                        (other_stats_dict.get(model, {}).get(id_) or {}).get(
                            "mean", None
                        )
                        - base["mean"]
                        if other_stats_dict.get(model, {}).get(id_)
                        else None
                    ),
                }
                for model in other_models
            },
        }
        full_comparison.append(result_entry)

    # Compute overall ranking based on average absolute deviation.
    overall_ranking = []
    for model in other_models:
        deviations = overall_deviations[model]
        if deviations:
            avg_dev = statistics.mean(deviations)
        else:
            avg_dev = None
        overall_ranking.append((model, avg_dev))
    overall_ranking.sort(key=lambda tup: (tup[1] is not None, tup[1]))

    print("\nOverall Ranking (by average absolute deviation from base):")
    print(f"{'Rank':<5}{'Model':<35}{'Avg Abs Diff':>15}")
    print("-" * 60)
    for rank, (model, avg_dev) in enumerate(overall_ranking, start=1):
        if avg_dev is not None:
            print(f"{rank:<5}{model:<35}{avg_dev:15.2f}")
        else:
            print(f"{rank:<5}{model:<35}{'N/A':>15}")
    print("-" * 60)

    # Dump full comparison details to a JSON file.
    output_file = "detailed_score_comparison.json"
    with open(output_file, "w") as f:
        json.dump(full_comparison, f, indent=4)


if __name__ == "__main__":
    main()
