"""
Vector store interface for semantic search over the agent's codebase.

Provides the :class:`VectorStore` class which wraps a
`ChromaDB <https://www.trychroma.com/>`_ persistent collection,
allowing the agent to retrieve relevant code context via embedding
similarity search.

Typical usage::

    store = VectorStore(path="./chroma_data")
    results = store.search("authentication middleware")
    context = store.get_context_string("how does the triage work")
    print(context)
"""

import chromadb
import os
from typing import List, Dict, Any, Optional


class VectorStore:
    """Manages a persistent ChromaDB collection for semantic search.

    Documents are stored alongside metadata (file path, chunk type,
    symbol name, parent scope) and can be queried by natural-language
    embedding similarity.

    Two convenience methods wrap the raw ChromaDB query:

    * :meth:`search` returns a structured list of result dictionaries.
    * :meth:`get_context_string` formats the results as a human-readable
      string ready to be injected into an LLM prompt.

    :param path: Filesystem path for the ChromaDB persistent storage.
    """

    def __init__(self, path):
        self.client = chromadb.PersistentClient(
            path=path,
            settings=chromadb.Settings(anonymized_telemetry=os.getenv("ANONYMIZED_TELEMETRY", False))
        )
        self.collection = self.client.get_or_create_collection("agentern_codebase")

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Query the ChromaDB collection by embedding similarity.

        Each result dict contains:

        * ``"content"`` (*str*) — The document text.
        * ``"metadata"`` (*dict*) — Associated metadata (file path,
          chunk type, symbol, parent, etc.).
        * ``"id"`` (*str*) — The document's unique identifier in the
          collection.
        * ``"distance"`` (*float* or ``None``) — The cosine / L2
          distance returned by ChromaDB (may be ``None`` if the
          collection does not expose distances).

        :param query: The natural-language query string.
        :param n_results: Maximum number of results to return.  Passed
            directly to ChromaDB's :meth:`chromadb.Collection.query`.
        :param where: An optional filter dictionary passed to ChromaDB's
            ``where`` clause, e.g. ``{"file": {"$contains": "auth"}}``.
        :returns: A list of result dictionaries.  Returns an empty list
            if the collection is empty or no matches are found.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        # Combine documents, metadatas, ids, distances into list
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        ids = results["ids"][0]
        distances = (
            results["distances"][0]
            if "distances" in results
            else [None] * len(docs)
        )

        return [
            {
                "content": doc,
                "metadata": meta,
                "id": id_,
                "distance": dist,
            }
            for doc, meta, id_, dist in zip(docs, metas, ids, distances)
        ]

    def get_context_string(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> str:
        """Query the collection and return a formatted string for LLM consumption.

        The output is a plain-text block with sections separated by
        ``"---"`` dividers.  Each section has a metadata header line
        (file, type, symbol, parent) followed by the document content.

        Example output::

            File: app/auth/middleware.py | Type: function | Symbol: login_required
            def login_required(f):
                ...
            ---
            File: app/auth/utils.py | Type: class | Symbol: TokenManager | Parent: auth
            class TokenManager:
                ...

        :param query: The natural-language query string.
        :param n_results: Maximum number of results to include in the
            formatted output.
        :param where: An optional filter dictionary passed to ChromaDB's
            ``where`` clause.
        :returns: A formatted string ready for injection into an LLM
            prompt.  Returns ``"No relevant context found."`` if the
            collection is empty or no matches are found.
        """
        results = self.search(query, n_results, where)
        if not results:
            return "No relevant context found."

        parts = []
        for r in results:
            meta = r["metadata"]
            file = meta.get("file", "unknown")
            chunk_type = meta.get("chunk_type", "")
            symbol = meta.get("symbol", "")
            parent = meta.get("parent", "")

            # Build a header
            header = f"File: {file}"
            if chunk_type:
                header += f" | Type: {chunk_type}"
            if symbol:
                header += f" | Symbol: {symbol}"
            if parent:
                header += f" | Parent: {parent}"

            parts.append(f"{header}\n{r['content']}")

        return "\n---\n".join(parts)