"""Semantic search using ChromaDB vector store."""

from __future__ import annotations

import logging
from typing import Any

from life_optimizer.storage.database import Database

logger = logging.getLogger(__name__)

# Try to import chromadb — it's an optional dependency
try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None  # type: ignore[assignment]
    CHROMADB_AVAILABLE = False
    logger.info("chromadb not installed — semantic search unavailable")


class SemanticSearch:
    """Vector-based semantic search using ChromaDB."""

    def __init__(self, persist_dir: str = "data/chromadb"):
        self._persist_dir = persist_dir
        self._client: Any = None
        self._collections: dict[str, Any] = {}

    def _get_client(self) -> Any:
        """Get or create the ChromaDB client."""
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("chromadb is not installed")
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        return self._client

    def _get_collection(self, name: str) -> Any:
        """Get or create a collection."""
        if name not in self._collections:
            client = self._get_client()
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    async def index_summary(
        self, summary_id: int, text: str, metadata: dict | None = None
    ) -> None:
        """Index a summary for semantic search.

        Args:
            summary_id: The summary ID.
            text: Summary text to index.
            metadata: Optional metadata to store.
        """
        if not CHROMADB_AVAILABLE:
            return
        collection = self._get_collection("summaries")
        meta = metadata or {}
        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_meta = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
        collection.upsert(
            ids=[str(summary_id)],
            documents=[text],
            metadatas=[clean_meta] if clean_meta else None,
        )

    async def index_event(
        self, event_id: int, text: str, metadata: dict | None = None
    ) -> None:
        """Index an event for semantic search.

        Args:
            event_id: The event ID.
            text: Event description text to index.
            metadata: Optional metadata to store.
        """
        if not CHROMADB_AVAILABLE:
            return
        collection = self._get_collection("events")
        meta = metadata or {}
        clean_meta = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
        collection.upsert(
            ids=[str(event_id)],
            documents=[text],
            metadatas=[clean_meta] if clean_meta else None,
        )

    async def search(
        self,
        query: str,
        collection: str = "summaries",
        n_results: int = 10,
    ) -> list[dict]:
        """Search for similar documents.

        Args:
            query: Search query text.
            collection: Collection to search ("summaries" or "events").
            n_results: Number of results to return.

        Returns:
            List of dicts with keys: id, text, metadata, distance.
        """
        if not CHROMADB_AVAILABLE:
            return []
        try:
            coll = self._get_collection(collection)
            # Ensure we don't request more results than available
            count = coll.count()
            if count == 0:
                return []
            actual_n = min(n_results, count)
            results = coll.query(query_texts=[query], n_results=actual_n)

            output = []
            if results and results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                documents = results["documents"][0] if results["documents"] else [None] * len(ids)
                metadatas = results["metadatas"][0] if results["metadatas"] else [None] * len(ids)
                distances = results["distances"][0] if results["distances"] else [None] * len(ids)

                for i, doc_id in enumerate(ids):
                    output.append({
                        "id": doc_id,
                        "text": documents[i] if i < len(documents) else None,
                        "metadata": metadatas[i] if i < len(metadatas) else None,
                        "distance": distances[i] if i < len(distances) else None,
                    })

            return output
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []

    async def reindex_all(self, db: Database) -> int:
        """Reindex all summaries and events from the database.

        Args:
            db: Database instance.

        Returns:
            Total number of documents indexed.
        """
        if not CHROMADB_AVAILABLE:
            logger.warning("chromadb not available, skipping reindex")
            return 0

        from life_optimizer.storage.repositories import EventRepository, SummaryRepository

        count = 0

        # Reindex summaries
        summary_repo = SummaryRepository(db)
        summaries = await summary_repo.get_summaries(limit=10000)
        for summary in summaries:
            await self.index_summary(
                summary.id,
                summary.summary_text,
                {
                    "period_type": summary.period_type,
                    "period_start": summary.period_start,
                    "period_end": summary.period_end,
                },
            )
            count += 1

        # Reindex events (only those with window titles)
        event_repo = EventRepository(db)
        events = await event_repo.get_events(limit=10000)
        for event in events:
            text_parts = [event.app_name]
            if event.window_title:
                text_parts.append(event.window_title)
            if event.category:
                text_parts.append(event.category)
            text = " | ".join(text_parts)
            await self.index_event(
                event.id,
                text,
                {
                    "app_name": event.app_name,
                    "timestamp": event.timestamp,
                    "category": event.category or "",
                },
            )
            count += 1

        logger.info("Reindexed %d documents", count)
        return count
