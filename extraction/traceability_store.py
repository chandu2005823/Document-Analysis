import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "traceability.json"
)


def save_traceability(records):
    """
    Save architecture traceability records
    as a JSON file.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            indent=4,
            ensure_ascii=False
        )


def load_traceability():
    """
    Load previously saved traceability records.
    """

    if not OUTPUT_FILE.exists():
        return []

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)