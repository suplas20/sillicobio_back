# sillicobio_back

SillicoBio LIMS backend scaffold based on the documents in `docs/`.

## Stack

- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL via psycopg
- Server-side session cookie auth

## Structure

```text
app/
  api/v1/endpoints/  API endpoint modules
  core/              app settings and auth helpers
  db/                SQLAlchemy engine/session setup
  models/            DB table mappings
  schemas/           request/response schemas
  crud/              DB access functions
  services/          business logic
  utils/             common response and exception helpers
alembic/             migration environment
tests/               test package
```

## Setup

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `DATABASE_URL` and `SESSION_SECRET_KEY` in `.env`.

## Run

```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or use the project script:

```bash
bash scripts/run-server.sh
```

Auto-reload can be enabled when the local filesystem allows file watching:

```bash
RELOAD=1 bash scripts/run-server.sh
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Postman

Import these two files into Postman:

- `postman/SillicoBio_LIMS_API.postman_collection.json`
- `postman/SillicoBio_LIMS_API.postman_environment.example.json`

After importing the example environment, set `adminPassword` locally. Select the environment, run `00 Auth / Login as admin`, then run the read-only smoke requests. Postman keeps the `SESSION` cookie automatically after login.
