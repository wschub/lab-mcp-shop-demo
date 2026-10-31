# MCP Shop Demo

Small product/user CRUD (FastAPI + PostgreSQL) exposed as a REST API and as an
MCP server (Streamable HTTP), so Claude can query stock, search products, manage
a cart, check out and read a best-seller KPI.

> A multi-user version (one token per user, per-user cart and orders) lives in
> the `feature/per-user-auth` branch.

## Stack
Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL · MCP Python SDK (`mcp<2`) · ngrok

## Structure
```
app/
  config.py      env vars (dotenv)
  database.py    engine and session
  models.py      users, products, cart_items, orders, order_items
  schemas.py     Pydantic models
  crud.py        business logic (cart, checkout, KPI, CSV import)
  main.py        REST API + MCP mounted at /mcp
  mcp_server.py  MCP tools
  auth.py        bearer-token middleware for /mcp
seed.py          sample data (8 products, 2 users)
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
createdb mcp_demo
cp .env.example .env        # fill DATABASE_URL and AUTH_TOKEN
python seed.py
uvicorn app.main:app --reload --port 8000
```

Generate a token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
If `AUTH_TOKEN` is empty, auth is disabled.

## MCP tools
`get_total_stock`, `list_products`, `search_products`, `get_product`,
`create_product`, `update_product`, `import_products_from_csv`, `view_cart`,
`add_to_cart`, `remove_from_cart`, `checkout`, `list_orders`, `get_top_product`.

Stock is only reduced when `checkout` completes.

## Connect to Claude
1. `ngrok http 8000`
2. In Claude: Settings → Connectors → Add custom connector
3. URL: `https://<your-subdomain>.ngrok-free.app/mcp`
4. Request header: `authorization: Bearer <AUTH_TOKEN>`
   If the header option isn't available in your plan, use `https://<subdomain>.ngrok-free.app/mcp?token=<AUTH_TOKEN>` with "No sign-in".

Example prompts: "What is the total stock?", "Add 2 keyboards to my cart and
check out", "What is the best-selling product?"

## REST API
Interactive docs at `http://localhost:8000/docs`.