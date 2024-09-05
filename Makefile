APPS:=./workflow

.PHONY: pretty lint test

pretty:
	black $(APPS)
	isort $(APPS)

lint:
	ruff check $(APPS)
	black $(APPS) --check
	isort $(APPS) --check-only

test:
	coverage run manage.py test $(APPS) && coverage combine && coverage report && coverage html && coverage erase
