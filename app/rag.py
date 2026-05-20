import re
import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.llm import synthesize_policy_answer
from app.schemas import Citation


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "who",
    "why",
    "should",
    "with",
}

SYNONYMS = {
    "files": {"evidence", "records", "documents"},
    "prove": {"evidence", "traceable", "supporting"},
    "proof": {"evidence", "traceable", "supporting"},
    "inspection": {"audit", "review"},
    "inspect": {"audit", "review"},
    "compliance": {"declaration", "approvals", "certificates"},
}


def _policy_answer_llm_enabled() -> bool:
    return os.getenv("RAG_POLICY_LLM", "true").lower() in ("1", "true", "yes")


@dataclass
class Chunk:
    document: str
    section: str
    text: str
    tokens: set[str]
    embedding: Optional[list[float]] = None


def tokenize(text: str) -> set[str]:
    tokens = {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS}
    expanded = set(tokens)
    for token in tokens:
        expanded.update(SYNONYMS.get(token, set()))
    return expanded


class PolicyRetriever:
    def __init__(self, corpus_dir: Path):
        self.corpus_dir = corpus_dir
        self.chunks = self._load_chunks()
        self.embedding_provider = os.getenv("RAG_EMBEDDING_PROVIDER", "ollama").lower()
        self._hydrate_embeddings()

    def _load_chunks(self) -> List[Chunk]:
        chunks: List[Chunk] = []
        for path in sorted(self.corpus_dir.glob("*.md")):
            document = path.stem.replace("_", " ").title()
            current_section = "Overview"
            current_lines: List[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("## "):
                    if current_lines:
                        text = "\n".join(current_lines).strip()
                        chunks.append(Chunk(document, current_section, text, tokenize(text)))
                    current_section = line.removeprefix("## ").strip()
                    current_lines = []
                elif not line.startswith("# "):
                    current_lines.append(line)
            if current_lines:
                text = "\n".join(current_lines).strip()
                chunks.append(Chunk(document, current_section, text, tokenize(text)))
        return [chunk for chunk in chunks if chunk.text]

    def answer(self, question: str) -> tuple[str, List[Citation]]:
        scored = self._embedding_scores(question)
        min_score = 0.45 if scored else 0.18
        if not scored:
            scored = self._keyword_scores(question)

        if not scored or scored[0][0] < min_score:
            return "I do not know based on the provided documents", []

        top_score = scored[0][0]
        selected = [chunk for score, chunk in scored[:2] if score >= max(min_score, top_score * 0.75)]
        citations = [Citation(document=chunk.document, section=chunk.section) for chunk in selected]
        context_blocks = [(chunk.document, chunk.section, chunk.text) for chunk in selected]
        if _policy_answer_llm_enabled():
            synthesized = synthesize_policy_answer(question, context_blocks)
            if synthesized:
                return synthesized, citations
        answer_parts = [chunk.text for chunk in selected]
        return " ".join(answer_parts), citations

    def _keyword_scores(self, question: str) -> list[tuple[float, Chunk]]:
        query_tokens = tokenize(question)
        if not query_tokens:
            return []

        scored = []
        for chunk in self.chunks:
            overlap = query_tokens & chunk.tokens
            score = len(overlap) / max(len(query_tokens), 1)
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)

        return scored

    def _embedding_scores(self, question: str) -> list[tuple[float, Chunk]]:
        if self.embedding_provider != "ollama":
            return []
        query_embedding = self._ollama_embedding(question)
        if not query_embedding:
            return []
        scored = []
        for chunk in self.chunks:
            if chunk.embedding:
                score = cosine_similarity(query_embedding, chunk.embedding)
                if score:
                    scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    def _hydrate_embeddings(self) -> None:
        if self.embedding_provider != "ollama":
            return
        if not self._ollama_available():
            return
        for chunk in self.chunks:
            chunk.embedding = self._ollama_embedding(chunk.text)
        if not all(chunk.embedding for chunk in self.chunks):
            for chunk in self.chunks:
                chunk.embedding = None

    def _ollama_embedding(self, text: str) -> Optional[list[float]]:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        payload = {"model": model, "prompt": text}
        try:
            request = urllib.request.Request(
                f"{base_url}/api/embeddings",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                body = json.loads(response.read().decode("utf-8"))
            embedding = body.get("embedding")
            return embedding if isinstance(embedding, list) else None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _ollama_available(self) -> bool:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=1):
                return True
        except (urllib.error.URLError, TimeoutError):
            return False


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
