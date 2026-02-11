APP?=lxp_qna_engine

.PHONY: venv install install-dev run dev fmt lint test sync req req-dev lock

# Create a uv-managed virtualenv (optional, uv will auto-manage if omitted)
venv:
	uv venv

# Export locked requirements from uv/pyproject
# Runtime only (no dev)
req requirements.txt:
	uv export --frozen --format requirements-txt -o requirements.txt

# Dev + extras (useful for local tooling/CI)
req-dev requirements-dev.txt:
	uv export --frozen --format requirements-txt --all-extras --dev -o requirements-dev.txt

# Update uv.lock from pyproject (if you changed deps)
lock:
	uv lock

# Install exact pinned deps from requirements.txt using uv (runtime install)
install: requirements.txt
	uv pip sync requirements.txt

# Install all deps including dev using uv (preferred for local dev and tests)
install-dev:
	uv sync --all-extras --dev

# Sync alias (runtime)
sync: install

# Run console script via uv
run:
	uv run lxp-qna-engine

# Dev server (hot reload)
dev:
	uv run uvicorn $(APP).cli:app --reload --factory

fmt:
	@echo "(placeholder)"

lint:
	@echo "(placeholder)"

# Run tests via uv (ensure dev deps installed)
test: install-dev
	uv run -m pytest -q
