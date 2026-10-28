"""CareOps AI - FastAPI backend.
Run:  cd Backend  ->  uvicorn main:app --reload   ->  open http://127.0.0.1:8000
Serves the API (/api/...), the knowledge-base PDFs (/docs/...) and the Frontend."""
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "AI"))     # so the agent can be imported
import services as s

app = FastAPI(title="CareOps AI", docs_url="/swagger", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- Dashboard ----------
@app.get("/api/summary")
def summary():
    return s.kpis(s.latest_rows())

@app.get("/api/departments")
def departments():
    return s.departments(s.latest_rows())

@app.get("/api/trend")
def trend(metric: str = "arrivals", hours: int = 48):
    return s.trend(metric, min(max(hours, 6), 168))

# ---------- Alerts ----------
@app.get("/api/alerts")
def alerts():
    return s.alerts(s.latest_rows())

@app.get("/api/alerts/history")
def alerts_history():
    return s.alert_history()

# ---------- ML ----------
@app.get("/api/forecast")
def forecast():
    return [{"hour": str(x["hour"]), "arrivals": x["arrivals"]} for x in s.forecast_arrivals(6)]

@app.get("/api/spike")
def spike():
    r = s.spike_status()
    return {**r, "timestamp": str(r["timestamp"])}

# ---------- Knowledge base ----------
@app.get("/api/documents")
def documents():
    return s.documents()

# ---------- Chatbot ----------
class ChatIn(BaseModel):
    message: str
    session_id: str = "default"

SESSIONS = {}   # session_id -> list of (role, text); simple in-memory chat history

@app.post("/api/chat")
def chat(body: ChatIn):
    try:
        from agent import graph            # loaded on first use (loads embeddings + LLM)
        history = SESSIONS.get(body.session_id, [])
        result = graph.invoke({"messages": history + [("user", body.message)]})
        answer = result["messages"][-1].content
        if isinstance(answer, list):       # some models return a list of parts
            answer = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in answer)
        SESSIONS[body.session_id] = (history + [("user", body.message), ("assistant", answer)])[-20:]
        return {"answer": answer}
    except Exception as e:
        print("CHAT ERROR:", repr(e))
        return {"answer": "Sorry, the assistant is not available right now. Please check the server."}

import threading

# Load the agent in the background at startup, so the first chat is fast
@app.on_event("startup")
def warm_up():
    threading.Thread(target=lambda: __import__("agent"), daemon=True).start()


@app.get("/api/health")
def health():
    return {"status": "ok"}

# ---------- Static files (PDFs + Frontend). Frontend mount must stay LAST ----------
app.mount("/docs", StaticFiles(directory=ROOT / "data" / "RAG_Pdfs"), name="docs")
app.mount("/", StaticFiles(directory=ROOT / "Frontend", html=True), name="frontend")
