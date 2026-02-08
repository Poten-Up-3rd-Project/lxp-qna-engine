PY?=python
PIP?=pip
APP?=lxp_qna_engine

.PHONY: venv install run dev fmt lint test

venv:
	$(PY) -m venv .venv
	. .venv/bin/activate

install:
	$(PIP) install -r requirements.txt

run:
	lxp-qna-engine

dev:
	uvicorn lxp_qna_engine.cli:app --reload --factory

fmt:
	@echo "(placeholder)"

lint:
	@echo "(placeholder)"

test:
	$(PY) -m pytest -q
