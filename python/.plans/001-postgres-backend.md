# Plan 001 — Postgres-backed pysample with containers, migrations, and layered tests

Replace the in-memory `_items` dict with PostgreSQL via async SQLAlchemy 2.0 + Alembic, containerize
both the API and the DB under Compose, and restructure the test suite into unit / integration / e2e
tiers with testcontainers — all gated by Ruff, strict pyright, pre-commit, and GitHub Actions.

## Confirmed decisions

| Topic | Decision |
| ----- | -------- |
| Database | PostgreSQL only — no SQLite fallback anywhere, including tests |
| ORM | SQLAlchemy 2.0 **async** + Alembic; Pydantic schemas kept separate from ORM models |
| E2E | testcontainers-python drives the containers (no manual `docker compose` in tests) |
| Static analysis | Ruff (lint + format), checked-in strict pyright config, pre-commit, GitHub Actions, security scanning |
| API surface | Keep the existing 6 endpoints and JSON shape unchanged. Pagination + timestamps are deferred. |

## Established facts

- `asyncpg` 0.31.0 declares Python 3.14 support — one driver covers both the app and Alembic's async
  template, so `psycopg` is not needed.
- `psycopg` 3.3.6 also supports 3.14 and remains the fallback if asyncpg causes trouble.
- `.devcontainer/devcontainer.json` is a bare `base:ubuntu` image with `forwardPorts` only — there is
  **no Docker feature**, which blocks Compose and testcontainers.
- `src/pysample/__init__.py` does `from pysample.app import app`, shadowing the `pysample.app`
  submodule. This forced the `import_module` workaround in `tests/conftest.py`.
- Current state: 17 passing tests against a module-level `_items` dict and `itertools.count` in
  `src/pysample/app.py`.
- `pyproject.toml` already has `[tool.pytest.ini_options]` with `testpaths`, `pythonpath`, and strict
  flags. Dev deps today are `httpx2`, `pytest`, `pytest-cov`.

## Phase 0 — Foundations

1. [x] Add the `ghcr.io/devcontainers/features/docker-outside-of-docker:1` feature to
   `.devcontainer/devcontainer.json` and forward port 5432. **Blocker** — nothing in Phases 4–5 runs
   without it, and it requires a container rebuild.
2. [x] Add `[tool.ruff]` / `[tool.ruff.lint]` to `pyproject.toml`: rule set `E,F,I,UP,B,SIM,S,ASYNC,PT,TC,RUF,ANN`
   with per-file-ignores of `S101,ANN` for `tests/**`. Ruff's `S` rules replace a standalone bandit
   dependency.
3. [x] Add `[tool.pyright]` with `typeCheckingMode = "strict"`, covering `src` and `tests`, so the editor
   and CI agree and the strict Pylance errors become reproducible.
4. [x] Add `.pre-commit-config.yaml`: ruff, ruff-format, pyright (local uv hook), check-yaml,
   end-of-file-fixer, trailing-whitespace, detect-private-key, uv-lock.
5. [x] Commit `.env.example`; extend `.gitignore` with `.env`, `.pytest_cache`, `.ruff_cache`,
   `.coverage`, `htmlcov`.

Steps 2–5 are independent of each other and of step 1.

**Deviations:** `TC` is also ignored in `tests/**` — TYPE_CHECKING blocks obscure fixture signatures
without buying anything in a test suite. `S104` is suppressed inline in `src/pysample/__init__.py`
because binding uvicorn to `0.0.0.0` is required inside a container.

## Phase 0.a — Database infrastructure

*Moved up from Phase 4. No code prerequisites — the `db` service is pure infrastructure. Doing it here
gives Phases 1–3 a real database to develop against instead of being written blind.*

**Requires a devcontainer rebuild before any later phase can be exercised.**

5a. [x] `compose.yaml` — the `db` service only: `postgres:18-alpine`, a `pg_isready` healthcheck, a
    named `pgdata` volume, `POSTGRES_*` values read from `.env`, and port 5432 published. The
    `migrate` and `api` services are appended later in Phase 4.
5b. [x] `.devcontainer/compose.yaml` — a `workspace` service for the devcontainer itself, built from
    the current base image, mounting the repo and declaring `depends_on: db`.
5c. [x] `.devcontainer/devcontainer.json` — switch from `image` to
    `dockerComposeFile: ["../compose.yaml", "compose.yaml"]`, `service: workspace`,
    `runServices: ["db"]`, `workspaceFolder: /workspaces/pysample`. Keep the
    `docker-outside-of-docker` feature, still needed for image builds and testcontainers in
    Phases 4–5.
5d. [x] Copy `.env.example` to `.env` and document the step in the README.
5e. [x] Verify after rebuild: `docker compose ps` shows `db` healthy and `pg_isready -h db` succeeds
    from inside the devcontainer.

**Networking decision:** the devcontainer joins the Compose network, so `db:5432` is the connection
target from the developer shell *and* from the `api` container in Phase 4 — one hostname everywhere.
The alternative (`docker-outside-of-docker` alone plus `host.docker.internal:5432`) avoids the
devcontainer rewrite but forces two different hostnames for the same database.

## Phase 1 — Config and DB layer

*Depends on Phases 0 and 0.a.*

6. [ ] `src/pysample/core/config.py` — pydantic-settings `Settings` with `env_prefix="PYSAMPLE_"`, a
   `SecretStr` password, and a computed `postgresql+asyncpg://` URL. Cached `get_settings()`.
7. [ ] `src/pysample/core/db.py` — `Base` (`DeclarativeBase` subclass), `create_async_engine`,
   `async_sessionmaker(expire_on_commit=False)`, and a `get_session()` dependency that commits on
   success and rolls back on exception.
8. [ ] `src/pysample/db/models.py` — `Item` ORM model using `Mapped` / `mapped_column`: identity BIGINT
   PK, `String(100)` name, nullable `String(500)` description, `Numeric(12,2)` price, `Boolean`
   `in_stock` defaulting to true, plus CHECK constraints mirroring the Pydantic rules.
9. [ ] `src/pysample/schemas.py` — move `ItemCreate` / `Item` out of `src/pysample/models.py` and add
   `model_config = ConfigDict(from_attributes=True)`. Delete `models.py`.
10. [ ] `src/pysample/db/repository.py` — thin `ItemRepository(session)` exposing `list_all`, `get`,
    `create`, `replace`, `delete`. ORM queries only, so there is no SQL injection surface.

## Phase 2 — Migrations

*Depends on Phase 1. Runs in parallel with Phase 3.*

11. [ ] `alembic init -t async migrations`. `alembic.ini` sets `script_location = migrations` and
    deliberately omits `sqlalchemy.url` so no credentials live in the repo.
12. [ ] Wire `migrations/env.py` to `Base.metadata` as `target_metadata`, read the URL from
    `get_settings()`, and enable `compare_type=True` and `compare_server_default=True`.
13. [ ] Autogenerate the initial `0001_create_items` revision and hand-review the generated DDL.
14. [ ] Document the workflow: `uv run alembic revision --autogenerate -m "..."`,
    `uv run alembic upgrade head`, `uv run alembic downgrade -1`.

## Phase 3 — App restructure

*Depends on Phase 1. Runs in parallel with Phase 2.*

15. [ ] `src/pysample/main.py` replaces `app.py`: a `create_app()` factory plus a `lifespan` that disposes
    the engine on shutdown, with a module-level `app = create_app()` for uvicorn.
16. [ ] `src/pysample/api/deps.py` — `SessionDep = Annotated[AsyncSession, Depends(get_session)]`.
17. [ ] `src/pysample/api/routes/health.py` and `.../items.py` — async handlers backed by the repository,
    grouped under `APIRouter(prefix="/items", tags=["items"])`. Same 6 endpoints, same JSON shape.
18. [ ] `src/pysample/__init__.py` exposes only `main()`. Drop the `app` re-export that shadows the
    submodule.
19. [ ] Delete the module-level `_items` dict and `_id_sequence` counter.

## Phase 4 — Containers

*The `db` service moved to Phase 0.a. What remains is the application image and the services that run
it — see the per-step notes below.*

20. [ ] `Dockerfile` — multi-stage build on `ghcr.io/astral-sh/uv:python3.14-*-slim`, `uv sync --frozen
    --no-dev`, a python-slim runtime stage that copies `.venv`, a non-root `app` user, `EXPOSE 8000`,
    a HEALTHCHECK hitting `/health`, and a uvicorn CMD.
    *Buildable today; Phase 3 only changes the CMD target from `pysample.app:app` to
    `pysample.main:app`.*
21. [ ] `.dockerignore` — `.venv`, `.git`, `__pycache__`, `.pytest_cache`, `tests`, `.env`.
    *No prerequisites.*
22. [ ] `compose.yaml` — append `migrate` (app image running `alembic upgrade head`, `depends_on` db
    healthy) and `api` (`depends_on` migrate with `service_completed_successfully`, port 8000) to the
    `db` service created in Phase 0.a. The app never auto-migrates at startup.
    *`migrate` needs Phase 2. `api` needs Phase 1 for settings and step 20 for the image.*
23. [ ] `compose.override.yaml` — bind-mount `./src` and run uvicorn with `--reload` for development.
    *No prerequisites beyond step 22.*

## Phase 5 — Tests

*Depends on Phases 2–4.*

24. [ ] Restructure into `tests/unit/`, `tests/integration/`, `tests/e2e/`. The root `tests/conftest.py`
    keeps only shared fixtures; the `import_module` + monkeypatch store-reset fixture is deleted
    because the in-memory store is gone.
25. [ ] `tests/unit/test_schemas.py` — port the validation cases from the current `tests/test_models.py`.
    No DB, no container.
26. [ ] `tests/integration/conftest.py` — a session-scoped `PostgresContainer` fixture that runs
    `alembic upgrade head` against the container (which doubles as migration validation), a
    function-scoped outer-transaction-and-rollback fixture for isolation, and an
    `httpx.AsyncClient(transport=ASGITransport(app))` with `app.dependency_overrides[get_session]`.
27. [ ] `tests/integration/test_items_api.py` — port every current endpoint test. IDs now come from a real
    sequence, so assert on returned IDs rather than hardcoding `1`.
28. [ ] `tests/e2e/` — testcontainers' `DockerCompose` boots the built image alongside the database and the
    tests exercise real HTTP: the container healthcheck plus a full create → get → replace → delete
    flow. Marked `@pytest.mark.e2e`.
29. [ ] pytest config — `pytest-asyncio` with `asyncio_mode = "auto"`, registered `integration` and `e2e`
    markers, and `-m "not e2e"` appended to the default `addopts`.

## Phase 6 — CI and docs

*Depends on Phase 5.*

30. [ ] `.github/workflows/ci.yml` — `lint` (ruff check, ruff format --check, pyright), `test` (unit +
    integration; Docker is available on ubuntu-latest), `e2e` (build the image, then run the e2e
    suite), and `audit` (`uv run pip-audit`). uv caching enabled, `uv sync --frozen`.
31. [ ] Rewrite the README: architecture, Compose quickstart, migration workflow, the three test tiers, an
    environment variable table, and the static analysis commands.

## Dependency changes

- **Runtime add:** `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.31`, `alembic>=1.14`, `pydantic-settings>=2.6`
- **Dev add:** `pytest-asyncio>=0.24`, `testcontainers[postgres]>=4.9`, `ruff>=0.8`, `pyright>=1.1`,
  `pre-commit>=4.0`, `pip-audit>=2.7`
- **Keep:** `httpx2`, `pytest`, `pytest-cov`

## Verification

1. `uv run ruff check . && uv run ruff format --check .`
2. `uv run pyright` reports 0 errors, matching the strict Pylance mode already active in the editor.
3. `uv run pytest tests/unit -q`
4. `uv run pytest tests/integration -q` (requires Docker)
5. `docker compose build` then `uv run pytest -m e2e`
6. `docker compose up -d`, then `curl :8000/health` and a full CRUD curl round-trip.
7. `docker compose down -v && docker compose up -d` proves the stack rebuilds from an empty volume.
8. `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head`
9. `uv run alembic revision --autogenerate -m "noop"` produces an **empty** migration, proving the
   models and migrations are in sync. Delete the noop revision afterwards.
10. `uv run pip-audit` and `uv run pre-commit run --all-files`

## Deferred TODO

Explicitly out of scope for this plan, recorded for future work:

- Pagination on `GET /items` (`limit` / `offset` or cursor) with an `X-Total-Count` header.
- `created_at` / `updated_at` columns using `server_default=func.now()` and `onupdate`, exposed on the
  `Item` response schema.
- `PATCH /items/{id}` for partial updates.
- A readiness probe (`/health/ready`) that issues a real `SELECT 1`.
- Structured JSON logging with request IDs, authentication and authorization, rate limiting.
- Production Compose or Kubernetes manifests, connection pool tuning, a coverage threshold gate.

## Risks and open items

- The devcontainer rebuild in Phase 0.a must land before any other phase can be exercised.
- `postgres:18` relocated `PGDATA` to `/var/lib/postgresql/18/docker` and moved `VOLUME` to
  `/var/lib/postgresql` (verified against the upstream Dockerfile). The `pgdata` volume mounts the
  parent accordingly — do not "fix" it to `/var/lib/postgresql/data`.
- `mise`/`uv` live in `~/.local/bin` and are activated from a chezmoi-managed `~/.zshrc`. If those
  dotfiles are not applied automatically on rebuild, the toolchain must be reinstalled by hand.
- `Numeric(12,2)` returns `Decimal`; verify that the JSON round-trip still yields `9.99` while the
  schema field stays a `float`. The alternatives are switching the schema to `Decimal` (which changes
  the JSON contract) or using `Double` and accepting float imprecision.
- Pin exact `testcontainers` and `pytest-asyncio` versions at implementation time — the PyPI page for
  testcontainers was CAPTCHA-blocked during research, so its 3.14 support is unconfirmed.
