# GreenPack EPR Reconciliation Service

Small FastAPI backend for the **Innotechwise Junior AI Engineer screening task**. It accepts monthly plastic declarations, reconciles them against a mock ERP feed, generates a plain-English compliance summary, and answers EPR policy questions from a small cited corpus.

## Features

- `POST /submit` validates and stores a monthly declaration.
- `GET /summary/{producer_id}/{month}` reconciles declaration data against `data/erp_feed.csv`.
- `POST /ask` retrieves policy excerpts from `data/policies`, then (by default) uses the configured LLM to write a short grounded answer; the response always includes document/section citations for the excerpts used. Set `RAG_POLICY_LLM=false` for extractive answers only (offline-friendly).
- Deterministic validation and reconciliation stay outside the LLM.
- LLM is used for reconciliation narrative summaries and, when enabled, for synthesized policy answers.
- Docker support for repeatable local review.

## Tech Choices

- API: FastAPI with Pydantic validation.
- Storage: SQLite in `data/greenpack.db`. It is simple, local, auditable, and enough for this assignment.
- ERP integration: CSV file in `data/erp_feed.csv`, representing a small exported feed from GreenPack's ERP.
- LLM: configurable through `LLM_PROVIDER`.
  - `ollama`: local Ollama with `llama3.2`.
  - `openai`: OpenAI Chat Completions when `OPENAI_API_KEY` is present.
- LLM fallback: deterministic summary text if Ollama is unavailable, so reviewers can still run the project without paid APIs.
- RAG/vector store: in-memory Markdown chunks. The retriever uses Ollama embeddings when available and falls back to domain-aware keyword retrieval when offline. After retrieval, an optional LLM step rephrases the answer strictly from those chunks (`RAG_POLICY_LLM`); if the LLM is unavailable or refuses, the service falls back to joining chunk text.
- Embedding model: `nomic-embed-text` via Ollama by default. This keeps the demo local and avoids paid API friction.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Optional Ollama setup:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ollama serve
```

If Ollama is not running, `/summary` still returns a deterministic offline narrative.

Optional OpenAI setup:

```bash
copy .env.example .env
```

Then set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in `.env`.

Docker:

```bash
docker compose up --build
```

The Compose file starts the API and an Ollama container. Pull `llama3.2` and `nomic-embed-text` inside the Ollama container before expecting generated summaries or embedding retrieval.

## Demo

PowerShell:

```powershell
.\scripts\demo.ps1
```

Bash:

```bash
bash scripts/demo.sh
```

The demo submits a declaration, calls reconciliation, and asks a policy question.

## Example Requests

Submit a declaration:

```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "Content-Type: application/json" \
  -d '{ "producer_id": "GREENPACK-001", "month": "2026-04", "declared_quantities_kg": { "rigid_plastic": 12000, "flexible_plastic": 8500, "multilayer_plastic": 3200 } }'
```

Get summary:

```bash
curl http://127.0.0.1:8000/summary/GREENPACK-001/2026-04
```

Ask a policy question:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{ "question": "What evidence should GreenPack keep for an audit?" }'
```

Unsupported questions return:

```json
{
  "answer": "I do not know based on the provided documents",
  "citations": []
}
```

## RAG Corpus Sources

The corpus uses fabricated mock policy notes for this assignment, allowed by the brief:

- `data/policies/producer_registration.md`
- `data/policies/category_reporting.md`
- `data/policies/target_compliance.md`
- `data/policies/audit_evidence.md`

Each answer cites the source document and section title.

## Validation Rules

`POST /submit` rejects:

- missing required fields
- negative category weights
- months outside `YYYY-MM` format
- missing or unknown plastic categories

The endpoint does not call an LLM because validation is deterministic.

## Reconciliation Logic

For each category:

```text
variance_kg = declared_kg - procured_kg
variance_percent = abs(variance_kg) / procured_kg * 100
flagged = variance_percent > 5
```

The endpoint returns both structured reconciliation rows and the narrative summary.

## Tests

```bash
pytest
```

Included test files:

- `tests/test_validation.py`
- `tests/test_reconciliation.py`
- `tests/test_rag.py`
- `tests/test_api.py`

The tests cover validation, the 5% reconciliation threshold, the zero-procurement edge case, supported RAG answers (extractive mode in CI), unsupported RAG refusal, and an API-level flow test for `/submit`, `/summary`, and `/ask`.

## Assignment alignment (screening brief)

This repository implements **Innotechwise — Junior AI Engineer Screening Task** (`Junior_AI_Engineer_Screening_Task_1.pdf`). Mapping:

| Brief requirement | In this repo |
|-------------------|--------------|
| `POST /submit` — deterministic validation (Pydantic), `record_id` + timestamp, no LLM | `app/schemas.py`, `app/storage.py`, `app/main.py` |
| `GET /summary/{producer_id}/{month}` — load declaration + mock ERP, flag **> 5%** variance, LLM **3–5 sentence** narrative from structured data | `app/reconciliation.py`, `app/llm.py`, `app/main.py`, `data/erp_feed.csv` |
| `POST /ask` — RAG over **3–5** docs, answers with **document + section** citations, refuse with exact **"I do not know based on the provided documents"** | `app/rag.py`, `data/policies/*.md` (four mock notes), citations in `AskResponse` |
| Sample **curl** / **script** — all three endpoints in sequence | README examples; `scripts/demo.ps1`, `scripts/demo.sh` |
| README: LLM + **embedding** choice and why; **storage** + **vector** approach; **AI assistant** usage; **one thing** with another day | Tech Choices, AI Coding Assistant Usage, What I Would Do Differently, RAG Corpus Sources |

**Not enforced by code (complete these for submission):** public **GitHub** link, **~90-second Loom** (see below), and reply on the **same channel** with **GitHub + Loom** links, **within the deadline** in the brief (typically **3 days** from receiving the task).

**From the brief:** reviewers score six dimensions (customer solution, API design, integration, LLM use, architectural judgment, vibe coding). Hitting **at least four** well is described as a strong submission—you do not need to excel at every dimension in code alone.

## Submission checklist

**Repository (before sharing the GitHub link):**

- `app/`
- `data/erp_feed.csv`
- `data/policies/`
- `tests/`
- `scripts/`
- `requirements.txt`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- `README.md`

**Per the PDF (full submission package):**

- Repository is **public** on GitHub (unless they specify otherwise).
- **~90-second Loom** with **(a)** demo, **(b)** AI-tool screen recording, **(c)** one architectural trade-off (see Loom section below).
- Send **GitHub link + Loom link** on the **same channel** you received the task, **before the deadline**.

## AI Coding Assistant Usage

I used Codex to scaffold the FastAPI project, split responsibilities into small modules, and generate the first pass of tests and documentation. I reviewed the deterministic logic manually, especially the validation boundary, zero-procurement reconciliation edge case, and the LLM/RAG fallback behavior.

## Architectural Tradeoff

I chose SQLite plus CSV because the assignment values clear integration boundaries more than infrastructure. ERP rows are cached after first load to avoid rereading the CSV on every summary request. For RAG, I chose local Ollama embeddings with a keyword fallback so the demo can run both with and without model setup. The tradeoff is that the in-memory vector layer is not durable and would need Chroma, pgvector, or another persistent index in production.

## What I Would Do Differently With Another Day

I would add real CPCB source documents, persist the embedding index in Chroma or pgvector, add auth around producer data, and build a small admin endpoint for refreshing ERP and policy indexes.

## Loom video (official brief: ~90 seconds total)

The PDF asks for a **~90 second** Loom with **three** segments. Keep each segment tight so the full video stays under the limit.

**(a) Demo — one flow end-to-end (brief: “one endpoint”; showing submit → summary is ideal)**  
Record `POST /submit` then `GET /summary/...` in the browser (`/docs`) or terminal (e.g. `demo.ps1`), so reviewers see validation, reconciliation JSON, and the narrative.

**(b) Vibe coding — visible AI interaction**  
Short screen recording of **Cursor / Claude Code / Copilot** (or similar) while you **write or refactor** one real slice of this repo (for example a test or a small function), not only the final code.

**(c) One architectural trade-off**  
One clear choice and why (good talking points: SQLite + CSV + cached ERP read; in-memory RAG + Ollama embeddings + keyword fallback; LLM only for narrative/synthesis with deterministic core; deterministic summary fallback when no model is up).

Optional if you have a few seconds left: a quick `POST /ask` with citations—still keep total time **~90 seconds**.
