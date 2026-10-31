# CareOps AI

AI based hospital operations dashboard for administrators. It shows live bed occupancy, ED waiting time and staff numbers, raises alerts from the hospital policy, forecasts the next 6 hours, and has a chatbot that answers from the policy PDFs and the database. It does not give medical advice. All data is synthetic.

## Folders
- `Backend/` FastAPI app, alert rules, database scripts
- `AI/` chatbot (LangGraph agent, PDF search, data tools)
- `ML/` forecast and anomaly models (notebooks, `train_forecasts.py`, `ml_tools.py`)
- `Frontend/` dashboard (HTML, CSS, JS)
- `data/` CSV data and policy PDFs, `Vector_Store/` search index for the PDFs
- `tests/` pytest tests

## Setup
1. Create a virtual environment and install packages
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. In PostgreSQL create a database named `careops`, then run `Backend/schema.sql` in it (pgAdmin Query Tool).
3. Copy `.env.example` to `.env` and fill in your database password and Groq key.
4. Load the data (takes about a minute): `python Backend/load_data.py`

## Run
```
cd Backend
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 in the browser. The API list is at http://127.0.0.1:8000/swagger

## Tests
```
pytest
```
The tests in `tests/test_api.py` need PostgreSQL running with the data loaded.

## Retrain or rebuild
- Forecast models: `python ML/train_forecasts.py`
- PDF search index (only if the PDFs change): `python AI/phase_1.py`

## Running on a server
Install the same packages, set the `.env` values, load the data and start with
`uvicorn main:app --host 0.0.0.0 --port 8000` from the `Backend` folder.
Put nginx or any reverse proxy in front if you want https.

## Note
The data ends on 10 Oct 2026, so "current" on the dashboard means the newest hour in the database.
