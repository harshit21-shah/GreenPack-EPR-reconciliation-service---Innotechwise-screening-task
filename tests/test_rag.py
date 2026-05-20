from pathlib import Path

from app.rag import PolicyRetriever


def test_rag_returns_citation_for_supported_question(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "keyword")
    monkeypatch.setenv("RAG_POLICY_LLM", "false")
    retriever = PolicyRetriever(Path("data/policies"))

    answer, citations = retriever.answer("What evidence should be kept for an audit?")

    assert "audit evidence pack" in answer.lower()
    assert citations
    assert citations[0].document
    assert citations[0].section


def test_rag_handles_paraphrased_supported_question(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "keyword")
    monkeypatch.setenv("RAG_POLICY_LLM", "false")
    retriever = PolicyRetriever(Path("data/policies"))

    answer, citations = retriever.answer("Which files prove compliance during inspection?")

    assert "submitted declaration" in answer.lower()
    assert citations


def test_rag_refuses_unsupported_question(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "keyword")
    monkeypatch.setenv("RAG_POLICY_LLM", "false")
    retriever = PolicyRetriever(Path("data/policies"))

    answer, citations = retriever.answer("What is the GST rate for laptops?")

    assert answer == "I do not know based on the provided documents"
    assert citations == []
