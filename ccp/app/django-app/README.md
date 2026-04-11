# ccp Django web application

Django + MongoDB + Redis port of the ccp Streamlit app at `ccp/app/`.
Preserves the original look (monospace, `#2c3e50` accent, custom Plotly
`ccp` template) and Portuguese UI copy.

## Local development

From the repository root:

```bash
uv sync --extra django-app
uv run python ccp/app/django-app/manage.py check
uv run python ccp/app/django-app/manage.py runserver
```

The settings module falls back to an in-memory cache and SQLite for
Django's own metadata when `MONGO_URL` and `REDIS_URL` are unset, so the
server starts without any external services. For the full experience set
both env vars (see `.env.example`) and launch the bundled services:

```bash
docker compose -f ccp/app/django-app/docker-compose.yml up -d mongo redis
export MONGO_URL=mongodb://localhost:27017/ccp
export REDIS_URL=redis://localhost:6379/0
uv run python ccp/app/django-app/manage.py runserver
```

## Container

```bash
docker compose -f ccp/app/django-app/docker-compose.yml up --build
```

The stack brings up `mongo:7`, `redis:7`, and the Django service listening
on `http://localhost:8000/`.

## Layout

```
ccp/app/django-app/
|-- manage.py
|-- ccp_web/                # project package (settings, urls, plotly theme wiring)
|-- templates/base.html     # shared layout: logo header, Plotly.js, HTMX, Alpine
|-- static/{css,img,js}/    # ccp theme, favicon, vendor JS shims
`-- apps/
    |-- home/               # Portuguese landing page
    |-- core/               # shared services (ccp wrapper, storage, exports)
    |-- straight_through/
    |-- back_to_back/
    |-- curves_conversion/
    |-- performance_evaluation/
    |-- reports/
    `-- integrations/       # AI, PI, Sentry (all optional)
```
