# Simple Makefile: create venv and install requirements
VENV=.venv
PYTHON=python3
PIP=$(VENV)/bin/pip

venv:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV) --prompt finance
	$(PIP) install --upgrade pip
	if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "🧹 Cleaned up virtual environment and cache files."

.PHONY: venv clean
