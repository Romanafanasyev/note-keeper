IMAGE := romaamor66/planbot
VERSION = $(shell cat VERSION)

.PHONY: run dev install-dev format lint test audit verify build scan push publish bump-patch bump-minor bump-major

run:
	python -m bot.main

dev: run

install-dev:
	python -m pip install --require-hashes -r requirements-dev.txt

format:
	python -m black .
	python -m isort .

lint:
	python -m black --check .
	python -m isort --check-only .
	python -m flake8 .

test:
	python -m pytest

audit:
	python -m pip_audit -r requirements.txt

verify: lint test audit

build:
	docker build --pull --platform linux/amd64 -t $(IMAGE):$(VERSION) .

scan:
	docker scout cves $(IMAGE):$(VERSION) --only-severity critical,high

push:
	docker push $(IMAGE):$(VERSION)

publish: verify build scan push

bump-patch:
	python scripts/bump_version.py patch

bump-minor:
	python scripts/bump_version.py minor

bump-major:
	python scripts/bump_version.py major
