# CareOps AI
Hospital operations intelligence (not for medical advice). Synthetic data only.

## Folders
- `Backend/` FastAPI app (`main.py`), data logic (`services.py`), alert rules (`alert_rules.py`), `schema.sql`, `load_data.py`
- `AI/` LangGraph agent (`agent.py`), RAG tool (`tools.py`), live-data tools (`data_tools.py`), `phase_1.py` builds the vector store
- `ML/` forecast + anomaly notebooks and `ml_tools.py`
- `Frontend/` HTML/CSS/JS dashboard
- `data/` CSV datasets and policy PDFs, `Vector_Store/` FAISS index

## Setup (once)
1. `python -m venv venv` then `venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Create database `careops` in pgAdmin, run `Backend/schema.sql` in its Query Tool (skip if tables exist)
4. Copy `.env.example` to `.env`, fill DATABASE_URL and GROQ_API_KEY
5. `python Backend/load_data.py` (loads 243,360 rows; safe to re-run)

## Run
```
cd Backend
uvicorn main:app --reload
```
Open http://127.0.0.1:8000  (API docs: /swagger)

## Rebuild vector store (only if PDFs change)
`python AI/phase_1.py`
