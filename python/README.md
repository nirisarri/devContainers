# pysample

A sample [FastAPI](https://fastapi.tiangolo.com/) application demonstrating a small REST API with
Pydantic-validated request models, typed responses, and standard HTTP status codes.

The API exposes a health check and CRUD operations over an in-memory collection of items.

> **Note:** items are stored in a module-level dictionary. Data resets on restart and is not shared
> across multiple worker processes. Replace it with a real database before deploying anything beyond
> a demo.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency and environment management
- Docker with Compose, for the PostgreSQL service
- [mise](https://mise.jdx.dev/) (optional) — pins the Python toolchain via [mise.toml](mise.toml)

## Setup

```bash
cp .env.example .env
uv sync
```

This creates a virtual environment in `.venv` and installs both runtime and dev dependencies.

## Infrastructure

PostgreSQL runs as a container defined in [compose.yaml](compose.yaml). The dev container joins the
same Compose project, so the database is reachable at `db:5432` from your shell and from the
application container alike.

```bash
docker compose up -d db     # VS Code already starts this via runServices
docker compose ps           # db should report (healthy)
pg_isready -h db -U pysample
docker compose down         # stop; add -v to also drop the data volume
```

Credentials come from `.env` (see [.env.example](.env.example)), which is not committed. Data
persists in the `pgdata` named volume.

## Running

```bash
uv run pysample
```

The server starts on <http://127.0.0.1:8000> with auto-reload enabled.

To run uvicorn directly (for example, to change host, port, or worker count):

```bash
uv run uvicorn pysample.app:app --host 0.0.0.0 --port 8000 --reload
```

### Interactive docs

Once running, FastAPI serves auto-generated API documentation:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

## API

| Method   | Path              | Description                  | Success status |
| -------- | ----------------- | ---------------------------- | -------------- |
| `GET`    | `/health`         | Liveness check               | `200`          |
| `GET`    | `/items`          | List all items               | `200`          |
| `GET`    | `/items/{id}`     | Fetch a single item          | `200`          |
| `POST`   | `/items`          | Create an item               | `201`          |
| `PUT`    | `/items/{id}`     | Replace an existing item     | `200`          |
| `DELETE` | `/items/{id}`     | Delete an item               | `204`          |

Unknown item IDs return `404`. Invalid request bodies return `422` with validation details.

### Item schema

| Field         | Type             | Constraints                  |
| ------------- | ---------------- | ---------------------------- |
| `id`          | `int`            | Assigned by the server       |
| `name`        | `str`            | 1–100 characters, required   |
| `description` | `str \| null`    | Up to 500 characters         |
| `price`       | `float`          | `>= 0`, required             |
| `in_stock`    | `bool`           | Defaults to `true`           |

### Example requests

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/items \
  -H 'Content-Type: application/json' \
  -d '{"name": "Widget", "description": "A useful widget", "price": 9.99}'

curl http://127.0.0.1:8000/items
curl http://127.0.0.1:8000/items/1
curl -X DELETE http://127.0.0.1:8000/items/1
```

## Development

### Project layout

```
src/pysample/
├── __init__.py       # exports `app`, plus `main()` which launches uvicorn
├── app.py            # FastAPI instance and route handlers
└── models.py         # Pydantic request/response models

tests/
├── conftest.py       # shared fixtures (TestClient, sample payload, store reset)
├── test_health.py    # health endpoint
├── test_items_api.py # items CRUD endpoints
└── test_models.py    # Pydantic model validation
```

### Managing dependencies

```bash
uv add <package>              # add a runtime dependency
uv add --dev <package>        # add a development dependency
uv sync                       # re-sync the environment after manual edits
```

### Testing

Tests use `pytest` with FastAPI's `TestClient` (backed by `httpx2`), which exercises the app
in-process without starting a server. Both are installed by `uv sync` as dev dependencies.

```bash
uv run pytest                  # run the suite
uv run pytest --cov=pysample   # run with coverage
uv run pytest tests/test_items_api.py::test_create_item
```

pytest is configured in [pyproject.toml](pyproject.toml) under `[tool.pytest.ini_options]`:
`testpaths` points at `tests/`, and `pythonpath = ["src"]` makes the package importable without an
editable install.

Because items live in a module-level dictionary, an autouse fixture in [tests/conftest.py](tests/conftest.py)
clears the store and resets the ID counter between tests so each test starts from a clean state.
ooo
  Error  21:57:39 msg_show.emsg E5108: Lua: [string "vim/_core/editor"]:353: nvim_exec2()[1]..BufReadPost Autocommands for "*": Vim(append):Lua callback: ...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:28: nvim_exec2()[1]..BufReadPost Autocommands for "*"..FileType Autocommands for "*": Vim(append):Lua callback: ...m/0.12.5/share/nvim/runtime/lua/vim/treesitter/query.lua:373: No parser for language "python"
stack traceback:
	[C]: in function 'assert'
	...m/0.12.5/share/nvim/runtime/lua/vim/treesitter/query.lua:373: in function 'fn'
	...ovim/0.12.5/share/nvim/runtime/lua/vim/func/_memoize.lua:82: in function 'fn'
	...ovim/0.12.5/share/nvim/runtime/lua/vim/func/_memoize.lua:82: in function 'get'
	.../share/nvim/lazy/LazyVim/lua/lazyvim/util/treesitter.lua:23: in function 'have_query'
	.../share/nvim/lazy/LazyVim/lua/lazyvim/util/treesitter.lua:40: in function 'have'
	...are/nvim/lazy/LazyVim/lua/lazyvim/plugins/treesitter.lua:166: in function 'attach'
	...are/nvim/lazy/LazyVim/lua/lazyvim/plugins/treesitter.lua:201: in function <...are/nvim/lazy/LazyVim/lua/lazyvim/plugins/treesitter.lua:200>
	[C]: in function 'nvim_cmd'
	...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:28: in function <...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:27>
	[C]: in function 'pcall'
	vim/_core/shared:1648: in function <vim/_core/shared:1628>
	[C]: in function '_with'
	...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:27: in function <...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:10>
	[C]: in function 'nvim_exec2'
	[string "vim/_core/editor"]:353: in function 'cmd'
	...hare/nvim/lazy/snacks.nvim/lua/snacks/picker/actions.lua:139: in function 'jump'
	...re/nvim/lazy/snacks.nvim/lua/snacks/explorer/actions.lua:326: in function 'fn'
	...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:362: in function <...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:357>
stack traceback:
	[C]: in function '_with'
	...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:27: in function <...e/installs/neovim/0.12.5/share/nvim/runtime/filetype.lua:10>
	[C]: in function 'nvim_exec2'
	[string "vim/_core/editor"]:353: in function 'cmd'
	...hare/nvim/lazy/snacks.nvim/lua/snacks/picker/actions.lua:139: in function 'jump'
	...re/nvim/lazy/snacks.nvim/lua/snacks/explorer/actions.lua:326: in function 'fn'
	...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:362: in function <...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:357>
stack traceback:
	[C]: in function 'nvim_exec2'
	[string "vim/_core/editor"]:353: in function 'cmd'
	...hare/nvim/lazy/snacks.nvim/lua/snacks/picker/actions.lua:139: in function 'jump'
	...re/nvim/lazy/snacks.nvim/lua/snacks/explorer/actions.lua:326: in function 'fn'
	...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:362: in function <...de/.local/share/nvim/lazy/snacks.nvim/lua/snacks/win.lua:357>

