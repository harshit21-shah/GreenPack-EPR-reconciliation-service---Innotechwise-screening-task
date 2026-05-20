from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.llm import generate_summary
from app.rag import PolicyRetriever
from app.reconciliation import load_erp_feed, reconcile
from app.schemas import AskRequest, AskResponse, DeclarationIn, DeclarationRecord, SummaryResponse
from app.storage import DeclarationStore


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

store = DeclarationStore(DATA_DIR / "greenpack.db")
retriever = PolicyRetriever(DATA_DIR / "policies")
app = FastAPI(title="GreenPack EPR Reconciliation Service", version="1.0.0")


@app.post("/submit", response_model=DeclarationRecord)
def submit_declaration(payload: DeclarationIn) -> DeclarationRecord:
    return store.save(payload)


@app.get("/summary/{producer_id}/{month}", response_model=SummaryResponse)
def get_summary(producer_id: str, month: str) -> SummaryResponse:
    declaration = store.get(producer_id, month)
    if declaration is None:
        raise HTTPException(status_code=404, detail="Declaration not found")

    erp_quantities = load_erp_feed(DATA_DIR / "erp_feed.csv", producer_id, month)
    rows = reconcile(declaration, erp_quantities)
    status = "needs_review" if any(row.flagged for row in rows) else "within_tolerance"
    narrative = generate_summary(producer_id, month, rows)
    return SummaryResponse(
        producer_id=producer_id,
        month=month,
        tolerance_percent=5.0,
        overall_status=status,
        reconciliation=rows,
        narrative=narrative,
    )


@app.post("/ask", response_model=AskResponse)
def ask_policy_question(payload: AskRequest) -> AskResponse:
    answer, citations = retriever.answer(payload.question)
    return AskResponse(answer=answer, citations=citations)
