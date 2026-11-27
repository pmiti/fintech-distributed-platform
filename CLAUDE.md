# Project Rules - fintech-distributed-platform

## Stack & Standards
- Python 3.12 managed with `uv`.
- FastAPI with async SQLAlchemy 2.0, Pydantic v2, and Alembic for PostgreSQL migrations.
- Celery + Redis for async background workers; MongoDB (Motor/PyMongo) for audit logs.
- Strict type hints across all modules.

## Architecture & Design Principles
- Clean separation of concerns per service: `domain/` (pure Python entities & business rules, zero framework imports), `application/` (use cases), `infrastructure/` (DB repositories, Redis, S3), `api/` (FastAPI routers & schemas).
- Apply SOLID principles pragmatically: use `typing.Protocol` or `ABC` for repository and publisher interfaces (Dependency Inversion & Interface Segregation).
- Use `@dataclass(frozen=True)` for Value Objects (e.g., `Money`) and encapsulated domain entities (`Account`).
- Keep files modular, concise, and easy to read. Never over-engineer.
