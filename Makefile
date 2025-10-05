SHELL := /bin/bash

.PHONY: run test lint openapi

run:
	uvicorn app.main:app --reload --port 8080

test:
	pytest -q

openapi:
	curl -sS http://localhost:8080/openapi.json | jq '.' > openapi.json

docker-build:
	docker build -t israel-transit-mvp:latest .

docker-run:
	docker run --rm -p 8080:8080 --env-file .env israel-transit-mvp:latest
