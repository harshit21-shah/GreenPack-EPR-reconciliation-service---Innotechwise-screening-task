# GreenPack EPR Reconciliation Service

Backend service for **GreenPack Industries** (fictional plastic packaging producer) to support monthly **EPR** (Extended Producer Responsibility) compliance in India.

Built for the **Innotechwise Junior AI Engineer screening task**. The service accepts plastic declarations, reconciles them against a mock ERP procurement feed, generates a plain-English compliance summary, and answers policy questions from a small document corpus with citations.

**Repository:** [github.com/harshit21-shah/GreenPack-EPR-reconciliation-service---Innotechwise-screening-task](https://github.com/harshit21-shah/GreenPack-EPR-reconciliation-service---Innotechwise-screening-task)

---

## What it does

| Endpoint | Purpose |
|----------|---------|
| `POST /submit` | Validate and store a monthly plastic declaration |
| `GET /summary/{producer_id}/{month}` | Reconcile declaration vs ERP; return structured rows + narrative |
| `POST /ask` | Answer EPR policy questions with document/section citations |

Interactive API docs: **http://127.0.0.1:8000/docs** (after starting the server).

---

## Quick start

### 1. Install and run

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Run all three endpoints (demo script)

**Windows (PowerShell):**

```powershell
.\scripts\demo.ps1
```

**macOS/Linux:**

```bash
bash scripts/demo.sh
```

### 3. Run tests

```bash
pytest
```

---

## Example requests

**Submit declaration**

```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "producer_id": "GREENPACK-001",
    "month": "2026-04",
    "declared_quantities_kg": {
      "rigid_plastic": 12000,
      "flexible_plastic": 8500,
      "multilayer_plastic": 3200
    }
  }'
```

**Reconciliation summary** (requires a prior submit for the same producer/month)

```bash
curl http://127.0.0.1:8000/summary/GREENPACK-001/2026-04
```

**Policy question**

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What evidence should GreenPack keep for an audit?"}'
```

**Off-corpus question** (no hallucination)

```json
{
  "answer": "I do not know based on the provided documents",
  "citations": []
}
```

---

## Endpoint behavior

### `POST /submit`

- Validates with **Pydantic**: required fields, `YYYY-MM` month, all three plastic categories, no negative weights.
- Persists to **SQLite** with generated `record_id` and UTC `created_at`.
- **Does not call an LLM** — validation and storage are deterministic.

### `GET /summary/{producer_id}/{month}`

1. Loads the stored declaration.
2. Loads procurement totals from **`data/erp_feed.csv`** (mock ERP export).
3. For each category, computes variance and flags if **absolute percent difference > 5%**.
4. Uses an **LLM** to write a **3–5 sentence** narrative from the structured reconciliation JSON (narrative only — not re-computing numbers).
5. Returns `reconciliation` rows plus `narrative` and `overall_status` (`within_tolerance` or `needs_review`).

**Reconciliation rule**

```text
variance_kg = declared_kg - procured_kg
variance_percent = abs(variance_kg) / procured_kg * 100   (0 procured: 0% if declared 0, else 100%)
flagged = variance_percent > 5
```

### `POST /ask`

1. Chunks **`data/policies/*.md`** by section.
2. Retrieves relevant chunks (Ollama embeddings when available; **keyword + synonym** fallback offline).
3. Optionally synthesizes a short answer from retrieved text only (`RAG_POLICY_LLM`, default `true`).
4. Returns **citations** (`document`, `section`) for chunks used.
5. If nothing matches confidently, returns the exact refusal string above with **empty citations**.

---

## Tech choices (per assignment brief)

### LLM — `llama3.2` via Ollama (default)

- **Why:** Matches Innotechwise’s local, no-cost workflow; reviewers can run without paid API keys.
- **Used for:** `/summary` narrative; optional grounded rephrasing on `/ask` when `RAG_POLICY_LLM=true`.
- **Alternative:** `LLM_PROVIDER=openai` with `OPENAI_API_KEY` (see `.env.example`).
- **Fallback:** Deterministic summary text and extractive policy answers when the model is unreachable.

### Embeddings — `nomic-embed-text` via Ollama

- **Why:** Local semantic retrieval for `/ask` without embedding API cost.
- **Fallback:** Domain-aware keyword retrieval with synonym expansion when embeddings are unavailable.

### Storage — SQLite (`data/greenpack.db`)

- **Why:** Simple, auditable, sufficient for a screening prototype; one declaration per producer/month.

### ERP integration — CSV (`data/erp_feed.csv`)

- **Why:** Clear integration boundary; easy for reviewers to inspect sample procurement data.
- ERP rows are **cached in memory** after first read to avoid re-parsing the CSV on every summary request.

### Vector store — in-memory chunk index

- **Why:** Small fixed corpus (four mock policy files); no extra infrastructure for a 4–6 hour task.
- **Trade-off:** Not durable across restarts; production would use Chroma, pgvector, or similar.

---

## RAG corpus sources

Mock policy notes (allowed by the brief; not legal advice):

| File | Topic |
|------|--------|
| `data/policies/producer_registration.md` | Producer onboarding |
| `data/policies/category_reporting.md` | Category reporting |
| `data/policies/target_compliance.md` | Target compliance |
| `data/policies/audit_evidence.md` | Audit evidence |

---

## Optional: Ollama and OpenAI

**Ollama (recommended for full demo)**

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ollama serve
```

**OpenAI**

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in `.env`.

**Environment variables**

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | `ollama` | Summary + policy synthesis provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `OLLAMA_MODEL` | `llama3.2` | Text generation |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Retrieval embeddings |
| `RAG_EMBEDDING_PROVIDER` | `ollama` | Use `keyword` for offline retrieval only |
| `RAG_POLICY_LLM` | `true` | `false` = extractive `/ask` answers only |

---

## Docker

```bash
docker compose up --build
```

Starts the API and an Ollama service. Pull `llama3.2` and `nomic-embed-text` inside the Ollama container before expecting LLM summaries or embedding-based retrieval.

---

## Project layout

```text
app/
  main.py           # FastAPI routes
  schemas.py        # Pydantic models + validation
  storage.py        # SQLite persistence
  reconciliation.py # ERP load + 5% variance logic
  llm.py            # Summary + grounded policy synthesis
  rag.py            # Chunking, retrieval, citations
data/
  erp_feed.csv      # Mock ERP procurement
  policies/         # RAG corpus (Markdown)
tests/              # pytest suite
scripts/            # demo.ps1, demo.sh
```

---

## Tests

```bash
pytest
```

| File | Covers |
|------|--------|
| `tests/test_validation.py` | Negative weights, invalid month |
| `tests/test_reconciliation.py` | 5% threshold, zero-procurement edge case |
| `tests/test_rag.py` | Supported questions, refusal, paraphrase |
| `tests/test_api.py` | End-to-end `/submit` → `/summary` → `/ask` |

---

## AI coding assistant usage

**Cursor** (and related tools) were used to scaffold the FastAPI layout, split modules, draft tests and documentation, and iterate on RAG/LLM fallback behavior.

**Reviewed manually:** validation rules, reconciliation math (including zero procured), retrieval score thresholds, and refusal handling so deterministic logic stays correct regardless of model availability.

---

## Architectural trade-off

**SQLite + CSV + in-memory RAG** instead of production ERP APIs and a persistent vector database.

- **Benefit:** Fast to ship, easy for reviewers to run and inspect; clear separation between deterministic compliance logic and LLM narrative.
- **Cost:** Not multi-tenant or production-hardened; embedding index is rebuilt on startup.

---

## What I would do with another day

- Ingest **real CPCB / public** policy PDFs into the corpus.
- Persist embeddings in **Chroma** or **pgvector**.
- Add **auth** per producer and an admin endpoint to refresh ERP and policy indexes.

---

## Author

**Harshit Shah** — Innotechwise Junior AI Engineer screening submission.
