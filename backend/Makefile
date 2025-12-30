.PHONY: up down logs ps restart init-db migrate celery test clean

# Variables
COMPOSE_FILE = docker-compose.yml

# Comandos Docker Compose
up:
	docker-compose -f $(COMPOSE_FILE) up -d

down:
	docker-compose -f $(COMPOSE_FILE) down

down-volumes:
	docker-compose -f $(COMPOSE_FILE) down -v

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-backend:
	docker-compose -f $(COMPOSE_FILE) logs -f backend

logs-celery:
	docker-compose -f $(COMPOSE_FILE) logs -f celery-worker

ps:
	docker-compose -f $(COMPOSE_FILE) ps

restart:
	docker-compose -f $(COMPOSE_FILE) restart

# Comandos de base de datos
init-db:
	docker-compose -f $(COMPOSE_FILE) exec backend python init_db.py

migrate:
	docker-compose -f $(COMPOSE_FILE) exec backend alembic upgrade head

makemigrations:
	docker-compose -f $(COMPOSE_FILE) exec backend alembic revision --autogenerate -m "$(m)"

# Comandos de aplicación
celery:
	docker-compose -f $(COMPOSE_FILE) exec celery-worker celery -A backend.celery_app:app worker --loglevel=info

celery-beat:
	docker-compose -f $(COMPOSE_FILE) exec celery-beat celery -A backend.celery_app:app beat --loglevel=info

shell:
	docker-compose -f $(COMPOSE_FILE) exec backend python

# Comandos de desarrollo
install:
	pip install -r requirements.txt

test:
	docker-compose -f $(COMPOSE_FILE) exec backend python -m pytest

clean:
	docker-compose -f $(COMPOSE_FILE) down -v
	docker system prune -f

# Ejecutar todo
all: up init-db migrate
	@echo "✅ Servicios iniciados y base de datos inicializada"
	@echo "🌐 FastAPI: http://localhost:8000"
	@echo "📚 Docs: http://localhost:8000/docs"
	@echo "🐘 PostgreSQL: localhost:5432"
	@echo "🗄️  Redis: localhost:6379"