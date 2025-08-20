# Backend Application

Python FastAPI backend for Cloud Explorer.

## Structure

- `app/` - Main application code
  - `routers/` - API route handlers
  - `services/` - Business logic and AWS integrations
  - `models/` - Pydantic data models
  - `core/` - Configuration and utilities
  - `tests/` - Test files

## Getting Started

1. Install dependencies:
   ```bash
   uv init
   uv add fastapi uvicorn boto3 python-dotenv pydantic
   ```

2. Copy environment file:
   ```bash
   cp .env.example .env
   ```

3. Run the application:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## Development Rules

- Follow the guidelines in `../DEVELOPMENT_RULES.md`
- Use type hints for all functions
- Maximum 300 lines per file
- Write tests for all new functionality
- Use async/await for I/O operations
