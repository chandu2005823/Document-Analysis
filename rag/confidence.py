def calculate_confidence(ranked_results):
    """
    Estimate confidence from the reranked retrieval results.

    This is a retrieval confidence indicator, not a
    statistical probability that the answer is correct.
    """

    if not ranked_results:
        return {
            "score": 0.0,
            "level": "Low"
        }

    top_score = ranked_results[0]["final_score"]

    # Difference between the strongest and second result
    if len(ranked_results) > 1:
        second_score = ranked_results[1]["final_score"]
        separation = top_score - second_score
    else:
        separation = top_score

    # Combine absolute relevance and ranking separation
    confidence_score = (
        0.75 * top_score
        +
        0.25 * min(separation * 5, 1.0)
    )

    confidence_score = max(
        0.0,
        min(confidence_score, 1.0)
    )

    if confidence_score >= 0.65:
        level = "High"
    elif confidence_score >= 0.45:
        level = "Medium"
    else:
        level = "Low"

    return {
        "score": confidence_score,
        "level": level
    }