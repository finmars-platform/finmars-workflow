VENV_NAME = venv
PYTHON = $(VENV_NAME)/bin/python
PIP = $(VENV_NAME)/bin/pip
COMPOSE = docker compose
SERVICE = web

.PHONY: env help venv test lint manage

help:
	@echo "Makefile commands:"
	@echo "  make env      		- Create env file from template"	
	@echo "  make venv     		- Create virtual environment"
	@echo "  make install  		- Install dependencies"
	@echo "  make freeze   		- Freeze dependencies"
	@echo "  make test     		- Run tests"
	@echo "  make lint     		- Lint the code"
	@echo "  make up       		- Run project"
	@echo "  make down	   		- Stop project"
	@echo "  make manage   		- Run manage.py command"
	@echo "  make manage-help	- Show available manage.py commands"

env:
	@if [ -f .env ]; then \
		read -p ".env already exists. Overwrite? (y/N): " ans; \
		if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
			cp .env.sample .env; \
			echo ".env overwritten."; \
		else \
			echo "Skipped creating .env."; \
		fi; \
	else \
		cp .env.sample .env; \
		echo ".env created from .env.sample."; \
	fi

venv:
	python3 -m venv $(VENV_NAME)

install: venv
	$(PIP) install -r requirements.txt

freeze: venv
	$(PIP) freeze > requirements.txt

test:
	$(COMPOSE) exec -i $(SERVICE) python manage.py test --keepdb

lint:
	$(COMPOSE) exec -i $(SERVICE) ruff format --exclude '**/migrations/*.py'

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

manage-help:
	$(COMPOSE) exec -T $(SERVICE) python manage.py help

manage:
	$(COMPOSE) exec -i $(SERVICE) python manage.py $(filter-out $@,$(MAKECMDGOALS))

%:
	@:
