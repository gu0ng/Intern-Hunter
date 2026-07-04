class VectorSearchPlaceholder:
    """Placeholder for V2/V3 Chroma or FAISS integration."""

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        return []

