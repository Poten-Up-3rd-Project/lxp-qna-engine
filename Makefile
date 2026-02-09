APP?=lxp_qna_engine

.PHONY: venv install run dev fmt lint test sync

# Create a uv-managed virtualenv (optional, uv will auto-manage if omitted)
venv:
	uv venv

# Install exact pinned deps from requirements.txt using uv
install:
	uv pip sync requirements.txt

# Sync alias
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

# Run tests via uv
test:
	uv run -m pytest -q
