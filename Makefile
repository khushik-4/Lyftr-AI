.PHONY: up down logs restart test test-backend

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down && docker compose up --build -d

test:
	cd backend && pytest -v

test-backend:
	cd backend && pytest -v
