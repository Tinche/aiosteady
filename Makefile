.PHONY: lint

lint:
	poetry run flake8 src/ tests stubs &&\
	poetry run mypy src tests