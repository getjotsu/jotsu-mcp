all:
.PHONY: all

all: flake8 coverage
.PHONY: all

flake8:
	flake8 jotsu tests
.PHONY: flake8

test:
	PYTHONPATH=. pytest -xv tests
.PHONY: test

coverage:
	PYTHONPATH=. pytest --cov=jotsu --cov-config=.coveragerc --cov-report=term-missing --cov-fail-under=100 -x tests/
.PHONY: coverage

build:
	python3 -m build
.PHONY: build

deploy: build
	python3 -m twine upload --verbose dist/*
.PHONY: deploy
