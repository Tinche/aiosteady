.PHONY: lint

lint:
	flake8 src/ tests stubs &&\
	mypy src tests