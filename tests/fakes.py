SAMPLE_ENTRIES = [
    {
        "name": "Spring (New)",
        "url": "https://www.shl.com/products/product-catalog/view/spring-new/",
        "test_type": ["K"],
        "description": "Knowledge of Spring core, AOP, IOC container and transactions.",
    },
    {
        "name": "SQL (New)",
        "url": "https://www.shl.com/products/product-catalog/view/sql-new/",
        "test_type": ["K"],
        "description": "Knowledge of SQL queries, data manipulation and transaction processing.",
    },
    {
        "name": "AI Skills",
        "url": "https://www.shl.com/products/product-catalog/view/ai-skills/",
        "test_type": ["P"],
        "description": "Behavioral readiness for applying AI in the workplace.",
    },
]


class FakeCatalogStore:
    """Drop-in replacement for CatalogStore that skips the embedding model entirely."""

    def __init__(self):
        self.legend = {"K": "Knowledge & Skills", "P": "Personality & Behavior"}
        self.assessments = SAMPLE_ENTRIES
        self._by_name = {e["name"].lower(): e for e in SAMPLE_ENTRIES}

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        return self.assessments[:top_k]

    def get_by_name(self, name: str) -> dict | None:
        return self._by_name.get(name.strip().lower())

    def is_valid_name(self, name: str) -> bool:
        return name.strip().lower() in self._by_name
