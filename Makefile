PYTHON ?= python

.PHONY: test lint init doctor destroy
test:
	$(PYTHON) -m pytest
lint:
	$(PYTHON) -m ruff check app cloud_deploy scripts tests
init:
	$(PYTHON) -m cloud_deploy init
doctor:
	$(PYTHON) -m cloud_deploy doctor
destroy:
	$(PYTHON) -m cloud_deploy destroy
