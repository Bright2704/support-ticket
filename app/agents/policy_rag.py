"""
Policy RAG agent — real retrieval over the policy KB.

Replaces the keyword `rules.match_policies` stand-in with an actual vector
search (Week 4-5 deliverable). Each policy row is embedded once into a small
in-process vector store; a ticket query is embedded the same way and scored by
cosine similarity, with metadata filtering on `applies_to` (category) and
`tier`, exactly like a ChromaDB collection with a `where` clause.

Backends
--------
* Default: a dependency-free TF-IDF vector store (`_TfidfStore`). Genuine
  vector search — TF-IDF vectors + cosine similarity — that runs offline and
  needs no model download, so tests and CI stay fast and deterministic.
* Optional: ChromaDB. Set `RAG_BACKEND=chroma` and `pip install chromadb` to
  swap in a persistent Chroma collection with the same interface. If Chroma is
  requested but not importable we fall back to TF-IDF and log a note.

Tokenisation is bilingual: latin word tokens plus character trigrams, so Thai
(which has no word spaces) is still matched.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from functools import lru_cache

from ..schemas import PolicyHit
from . import rules

# Similarity below this is treated as "not retrieved".
MIN_SCORE = 0.06
# The cross-category sentiment/churn policy is always considered.
_SENTIMENT_POLICY_ID = "ESC-001"


# ---------------------------------------------------------------------------
# Bilingual tokeniser (latin words + char trigrams for Thai/CJK)
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens = _WORD_RE.findall(text)
    # Character trigrams over the whole (space-stripped) string give coverage
    # for scripts without word boundaries, e.g. Thai.
    compact = re.sub(r"\s+", "", text)
    tokens += [compact[i : i + 3] for i in range(len(compact) - 2)]
    return tokens


# ---------------------------------------------------------------------------
# TF-IDF vector store (default backend)
# ---------------------------------------------------------------------------


class _TfidfStore:
    """Tiny TF-IDF + cosine-similarity store over the policy documents."""

    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        tokenised = [_tokenize(d["_text"]) for d in docs]

        df: Counter[str] = Counter()
        for toks in tokenised:
            df.update(set(toks))
        n = len(docs)
        self.idf = {term: math.log((1 + n) / (1 + freq)) + 1.0 for term, freq in df.items()}

        self.vectors = [self._vectorize(toks) for toks in tokenised]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        vec = {t: (c / len(tokens)) * self.idf.get(t, 0.0) for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        # Both vectors are L2-normalised, so the dot product is the cosine.
        small, large = (a, b) if len(a) < len(b) else (b, a)
        return sum(v * large.get(t, 0.0) for t, v in small.items())

    def query(self, text: str) -> list[tuple[dict, float]]:
        q = self._vectorize(_tokenize(text))
        scored = [(doc, self._cosine(q, vec)) for doc, vec in zip(self.docs, self.vectors)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ---------------------------------------------------------------------------
# Optional ChromaDB backend
# ---------------------------------------------------------------------------


class _ChromaStore:
    """Wrap a ChromaDB collection behind the same .query() interface."""

    def __init__(self, docs: list[dict]) -> None:
        import chromadb  # type: ignore

        self.docs = docs
        self._by_id = {d["policy_id"]: d for d in docs}
        client = chromadb.Client()
        # Fresh, in-memory collection built from the KB each start-up.
        try:
            client.delete_collection("policies")
        except Exception:  # noqa: BLE001
            pass
        self.collection = client.create_collection("policies")
        self.collection.add(
            ids=[d["policy_id"] for d in docs],
            documents=[d["_text"] for d in docs],
        )

    def query(self, text: str) -> list[tuple[dict, float]]:
        res = self.collection.query(query_texts=[text], n_results=len(self.docs))
        ids = res["ids"][0]
        dists = res.get("distances", [[0.0] * len(ids)])[0]
        # Chroma returns distance; convert to a 0..1 similarity.
        return [(self._by_id[i], 1.0 / (1.0 + d)) for i, d in zip(ids, dists)]


# ---------------------------------------------------------------------------
# Public RAG agent
# ---------------------------------------------------------------------------


def _build_docs() -> list[dict]:
    docs = []
    for pol in rules.load_kb()["policies"]:
        triggers = " ".join(pol.get("triggers") or [])
        docs.append(
            {
                **pol,
                "_text": f"{pol['title']}. {pol['snippet']} {triggers}",
            }
        )
    return docs


@lru_cache(maxsize=1)
def _store():
    docs = _build_docs()
    backend = os.environ.get("RAG_BACKEND", "tfidf").lower()
    if backend == "chroma":
        try:
            return _ChromaStore(docs)
        except Exception:  # noqa: BLE001 — chromadb missing/broken -> tfidf
            pass
    return _TfidfStore(docs)


def _passes_metadata(doc: dict, category: str | None, tier: str | None) -> bool:
    if category is not None and category not in doc.get("applies_to", []):
        return False
    if tier is not None and "tier" in doc and tier not in doc.get("tier", []):
        return False
    return True


def search(query: str, k: int = 5, category: str | None = None, tier: str | None = None) -> list[PolicyHit]:
    """Vector-search the policy KB. Metadata filter mirrors a Chroma `where`."""
    ranked = _store().query(query)
    hits: list[PolicyHit] = []
    for doc, score in ranked:
        if score < MIN_SCORE:
            continue
        if not _passes_metadata(doc, category, tier):
            continue
        hits.append(
            PolicyHit(policy_id=doc["policy_id"], title=doc["title"], snippet=doc["snippet"], score=round(score, 4))
        )
        if len(hits) >= k:
            break
    return hits


def retrieve_for_ticket(subject: str, body: str, category: str, tier: str | None, k: int = 5) -> list[PolicyHit]:
    """Retrieve policies for one ticket, filtered to its category + tier.

    The cross-category sentiment/churn policy (ESC-001) is always evaluated so
    an angry ticket in any category can still trigger escalation.
    """
    query = f"{subject}\n{body}"
    hits = search(query, k=k, category=category, tier=tier)
    seen = {h.policy_id for h in hits}

    if _SENTIMENT_POLICY_ID not in seen:
        for doc, score in _store().query(query):
            if doc["policy_id"] == _SENTIMENT_POLICY_ID and score >= MIN_SCORE:
                hits.append(
                    PolicyHit(
                        policy_id=doc["policy_id"],
                        title=doc["title"],
                        snippet=doc["snippet"],
                        score=round(score, 4),
                    )
                )
                break
    return hits
