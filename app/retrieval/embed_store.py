import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog" / "catalog.json"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


def _entry_to_text(entry: dict) -> str:
    type_names = entry.get("test_type", [])
    job_levels = ", ".join(entry.get("job_levels", []))

    return (
        f"{entry['name']}. "
        f"Test type: {', '.join(type_names)}. "
        f"Job levels: {job_levels}. "
        f"{entry.get('description', '')}"
    )


class CatalogStore:
    def __init__(self, catalog_path: Path = CATALOG_PATH):
        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)

        self.legend: dict[str, str] = data["test_type_legend"]
        self.assessments: list[dict] = data["assessments"]

        self._by_name = {
            a["name"].lower(): a
            for a in self.assessments
        }

        self._model = SentenceTransformer(EMBED_MODEL_NAME)

        texts = [_entry_to_text(a) for a in self.assessments]

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
        )

        embeddings = np.asarray(
            embeddings,
            dtype="float32",
        )

        self.index = faiss.IndexFlatIP(
            embeddings.shape[1]
        )

        self.index.add(embeddings)

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        if not self.assessments:
            return []

        top_k = min(top_k, len(self.assessments))

        query_vec = self._model.encode(
            [query],
            normalize_embeddings=True,
        )

        query_vec = np.asarray(
            query_vec,
            dtype="float32",
        )

        scores, indices = self.index.search(
            query_vec,
            top_k,
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            entry = dict(self.assessments[idx])
            entry["_score"] = float(score)
            results.append(entry)

        return results

    def get_by_name(self, name: str) -> dict | None:
        query = name.strip().lower()

        # Exact match
        if query in self._by_name:
            return self._by_name[query]

        # Partial match
        for full_name, assessment in self._by_name.items():
            if query in full_name:
                return assessment

        return None

    def is_valid_name(self, name: str) -> bool:
        return name.strip().lower() in self._by_name