.PHONY: test lint

test:
	pdm run pytest -xl tests/

lint:
	pdm run flake8 src/ tests stubs &&\
	pdm run mypy src tests
