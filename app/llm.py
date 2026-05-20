import json
import os
import urllib.error
import urllib.request
from typing import List, Optional, Sequence

from app.schemas import CategoryReconciliation


def _policy_context_prompt(question: str, context_blocks: Sequence[tuple[str, str, str]]) -> str:
    parts = [
        "Answer the user's question using ONLY the numbered policy excerpts below.",
        "Rules:",
        "- Write 2-5 sentences in plain English.",
        "- Use only facts that appear in the excerpts. Do not invent penalties, deadlines, or legal claims.",
        '- If the excerpts do not contain enough information to answer, reply with exactly: I do not know based on the provided documents',
        "- Do not list citation labels in your answer; cite sources are attached separately by the system.",
        "",
        "Excerpts:",
    ]
    for i, (document, section, text) in enumerate(context_blocks, start=1):
        parts.append(f"[{i}] Document: {document} | Section: {section}")
        parts.append(text.strip())
        parts.append("")
    parts.append(f"User question: {question.strip()}")
    return "\n".join(parts).strip()


def synthesize_policy_answer(question: str, context_blocks: Sequence[tuple[str, str, str]]) -> Optional[str]:
    """Grounded answer from retrieved chunks; returns None so caller can fall back to extractive text."""
    if not context_blocks:
        return None
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "openai":
        return _synthesize_policy_openai(question, context_blocks)
    return _synthesize_policy_ollama(question, context_blocks)


def _synthesize_policy_ollama(
    question: str,
    context_blocks: Sequence[tuple[str, str, str]],
) -> Optional[str]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "stream": False,
        "prompt": _policy_context_prompt(question, context_blocks),
    }
    try:
        request = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = str(body.get("response", "")).strip()
        if not text or text == "I do not know based on the provided documents":
            return None
        return text
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def _synthesize_policy_openai(
    question: str,
    context_blocks: Sequence[tuple[str, str, str]],
) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    user_content = _policy_context_prompt(question, context_blocks)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You answer EPR policy questions strictly from the excerpts in the user message. "
                    "Follow the rules in the user message exactly."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
    }
    try:
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"].strip()
        if not text or text == "I do not know based on the provided documents":
            return None
        return text
    except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def _fallback_summary(producer_id: str, month: str, rows: List[CategoryReconciliation]) -> str:
    flagged = [row for row in rows if row.flagged]
    if not flagged:
        return (
            f"For {producer_id} in {month}, declared plastic quantities are within the 5% tolerance "
            "when compared with the ERP procurement feed. The compliance team should retain the ERP "
            "extract and declaration record as audit evidence. No immediate correction is required."
        )
    gaps = "; ".join(
        f"{row.category} differs by {row.variance_percent}% ({row.variance_kg} kg)"
        for row in flagged
    )
    return (
        f"For {producer_id} in {month}, the reconciliation found material gaps: {gaps}. "
        "The compliance officer should review source invoices, check whether procurement was booked "
        "in the correct month, and correct the EPR declaration before filing."
    )


def generate_summary(producer_id: str, month: str, rows: List[CategoryReconciliation]) -> str:
    """Use the configured LLM when available; fall back to deterministic text for offline demos."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "openai":
        return _generate_openai_summary(producer_id, month, rows)
    return _generate_ollama_summary(producer_id, month, rows)


def _summary_prompt(producer_id: str, month: str, rows: List[CategoryReconciliation]) -> str:
    return (
        "Write a 3-5 sentence compliance summary in plain English. "
        "Do not redo calculations; use only the supplied JSON. "
        "Explain material gaps and recommend one action.\n\n"
        f"Producer: {producer_id}\nMonth: {month}\n"
        f"Reconciliation JSON: {[row.model_dump() for row in rows]}"
    )


def _generate_ollama_summary(
    producer_id: str,
    month: str,
    rows: List[CategoryReconciliation],
) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "stream": False,
        "prompt": _summary_prompt(producer_id, month, rows),
    }
    try:
        request = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = str(body.get("response", "")).strip()
        return text or _fallback_summary(producer_id, month, rows)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return _fallback_summary(producer_id, month, rows)


def _generate_openai_summary(
    producer_id: str,
    month: str,
    rows: List[CategoryReconciliation],
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_summary(producer_id, month, rows)

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You write concise compliance summaries from structured reconciliation data.",
            },
            {"role": "user", "content": _summary_prompt(producer_id, month, rows)},
        ],
        "temperature": 0.2,
    }
    try:
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"].strip()
        return text or _fallback_summary(producer_id, month, rows)
    except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return _fallback_summary(producer_id, month, rows)
