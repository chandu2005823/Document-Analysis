import re


STOP_WORDS = {
    "this",
    "that",
    "these",
    "those",
    "using",
    "with",
    "from",
    "into",
    "than",
    "their",
    "there",
    "about",
    "which",
    "where",
    "when",
    "what",
    "main",
    "primary",
    "described",
    "describe",
    "architecture",
    "using",
    "view",
    "views",
    "book",
    "called",
    "document",
    "titled",
    "author",
    "written",
    "published"
}


def normalize_words(text):
    """
    Convert text into meaningful lowercase words.
    """

    words = re.findall(r"\b[^\W\d_]{4,}\b", text.lower(), flags=re.UNICODE)

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def normalize_all_words(text):
    return set(re.findall(r"\b[^\W\d_]{4,}\b", text.lower(), flags=re.UNICODE))


def extract_key_phrases(text):
    """
    Extract important multi-word phrases that should
    receive stronger grounding weight.
    """

    text = text.lower()

    phrases = [
        "structural architecture",
        "structural architecture view",
        "behavioral architecture",
        "behavioral architecture view",
        "structural view",
        "behavioral view",
        "architecture views",
        "architecture description",
        "adaptive platform"
    ]

    return {
        phrase
        for phrase in phrases
        if phrase in text
    }


def sentence_support_score(sentence, context):
    """
    Calculate a heuristic support score.

    This is an application-level grounding indicator,
    not a probability of correctness.
    """

    sentence_words = normalize_words(sentence)
    context_words = normalize_words(context)

    if not sentence_words:
        return 1.0

    matched_words = (
        sentence_words.intersection(context_words)
    )

    word_score = (
        len(matched_words) /
        len(sentence_words)
    )

    sentence_phrases = extract_key_phrases(
        sentence
    )

    context_phrases = extract_key_phrases(context)
    context_words_all = normalize_all_words(context)
    matched_phrases = {
        phrase
        for phrase in sentence_phrases
        if phrase in context_phrases
        or set(phrase.split()).issubset(context_words_all)
    }

    if sentence_phrases:

        phrase_score = (
            len(matched_phrases) /
            len(sentence_phrases)
        )

    else:

        phrase_score = 0.0

    # Give stronger importance to explicit
    # architectural terminology.
    final_score = (
        0.60 * word_score
        + 0.40 * phrase_score
    )

    return final_score


def check_grounding(
    answer,
    context,
    threshold=0.30
):
    """
    Check each generated answer sentence
    against the retrieved context.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        answer.strip()
    )

    results = []

    for sentence in sentences:

        if not sentence.strip():
            continue

        score = sentence_support_score(
            sentence,
            context
        )

        results.append({
            "sentence": sentence,
            "score": score,
            "supported": score >= threshold
        })

    if not results:

        return {
            "supported": False,
            "score": 0.0,
            "sentences": []
        }

    overall_score = sum(
        result["score"]
        for result in results
    ) / len(results)

    all_supported = all(
        result["supported"]
        for result in results
    )

    return {
        "supported": all_supported,
        "score": overall_score,
        "sentences": results
    }