PYTHON ?= python

.PHONY: test lint init destroy
test:
	$(PYTHON) -m pytest
lint:
	$(PYTHON) -m ruff check app scripts tests
init:
	$(PYTHON) scripts/manage.py init
destroy:
	$(PYTHON) scripts/manage.py destroy
