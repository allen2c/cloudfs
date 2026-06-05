.PHONY: install upgrade fmt

install:
	poetry install -E all

update:
	poetry update
	poetry export \
		--format requirements.txt \
		--output requirements.txt \
		--without-hashes

fmt:
	isort cloudfs tests
	black cloudfs tests
	ruff check cloudfs tests --fix
