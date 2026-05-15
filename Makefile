.PHONY: install upgrade format_all

install:
	poetry install -E all

update:
	poetry update
	poetry export \
		--format requirements.txt \
		--output requirements.txt \
		--without-hashes
	poetry export \
		--format requirements.txt \
		--output requirements_all.txt \
		--without-hashes \
		--with dev \
		--all-extras

format:
	isort cloudfs tests
	black cloudfs tests
