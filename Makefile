# Makefile

# 🔧 Dev
run:
	python -m bot.main

dev: run

format:
	black .
	isort .

# 🔁 Docker + Версионирование
VERSION := $(shell cat VERSION)

bump:
	@python scripts/bump_version.py

build:
	docker build -t romaamor66/planbot:$(VERSION) .

push:
	docker push romaamor66/planbot:$(VERSION)

deploy: bump build push
	@echo "🔥 VERSION $(VERSION) деплоится! Не забудь пересоздать контейнер на сервере."
