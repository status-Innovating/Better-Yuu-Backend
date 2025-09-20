# Better-Yuu-Backend

This is the backend for the Better-Yuu application.

yuu_backend/
├──.github/                    # CI/CD workflows (e.g., deploy-to-cloud-run.yml)
├──.vscode/                    # VSCode settings for consistent development environment
├── app/                        # Main application source code
│   ├── __init__.py
│   ├── api/                    # API router aggregation and versioning
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/      # Individual feature routers are defined here
│   │           ├── __init__.py
│   │           ├── ai_engine.py
│   │           ├── auth.py
│   │           ├── dreams.py
│   │           ├── forums.py
│   │           └── groups.py
│   ├── core/                   # Core application logic and configuration
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic settings management for env variables
│   │   └── security.py         # Password hashing, JWT creation/validation
│   ├── db/                     # Database session management and base models
│   │   ├── __init__.py
│   │   ├── base.py             # Declarative base for SQLAlchemy models
│   │   └── session.py          # Database session dependency
│   ├── domains/                # Business logic, separated by domain
│   │   ├── __init__.py
│   │   ├── ai_engine/
│   │   │   ├── __init__.py
│   │   │   ├── prompts.py      # Prompt templates and engineering logic
│   │   │   ├── services.py     # Logic for calling LLMs, crisis detection
│   │   │   └── schemas.py      # Pydantic schemas for AI inputs/outputs
│   │   ├── dreams/
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # SQLAlchemy models for dreams, symbols
│   │   │   ├── services.py     # Business logic (CRUD, analysis triggers)
│   │   │   └── schemas.py      # Pydantic schemas for dream API
│   │   ├── groups/
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # Models for groups, members, messages
│   │   │   ├── services.py     # Logic for group lifecycle, check-ins
│   │   │   └── schemas.py      # Schemas for group API
│   │   └── users/
│   │       ├── __init__.py
│   │       ├── models.py       # User model (pseudonymous)
│   │       ├── services.py     # User creation, profile management
│   │       └── schemas.py      # User schemas (creation, public view)
│   ├── main.py                 # FastAPI application entry point
│   └── ws/                     # WebSocket connection management
│       ├── __init__.py
│       └── connection_manager.py # Handles WebSocket connections for groups
├── scripts/                    # Utility and operational scripts
│   └── seed_db.py              # Script to populate DB with initial data
├── tests/                      # Pytest tests, mirroring the app structure
│   ├── __init__.py
│   ├── api/
│   └── domains/
├──.dockerignore
├──.env.example                # Example environment variables
├──.gitignore
├── Dockerfile                  # Docker configuration for production
├── pyproject.toml              # Dependency management with Poetry/uv
└── README.md


users document (Mongo JSON)
{
  "_id": { "$oid": "655f1a1e9c8a4a0b5fbe1234" },
  "email": "anya@university.edu",
  "password_hash": "$2b$12$X...hashed...",            // stored but never returned to client
  "name": "Anya Rao",
  "display_name": "Anya",
  "pseudonym": "YuuFriend947",
  "is_mentor": false,
  "roles": [],
  "preferences": { "timezone": "Asia/Kolkata", "language": "en", "notifications": {...} },
  "onboarding": { "goals": ["sleep"], "availability": "20:00-22:00" },
  "embeddings": null,
  "consent": { "terms": true, "data_sharing": false, "date_accepted": "2025-09-10T08:30:00Z" },
  "status": "active",
  "moderation": { "flags": 0, "last_flagged_at": null },
  "created_at": { "$date": "2025-09-10T08:30:00Z" }
}


dreams document (Mongo JSON)
{
  "_id": { "$oid": "666a2b9f5bdc4d12a9e81234" },
  "user_id": "655f1a1e9c8a4a0b5fbe1234",           // store as string ref to user id (or use Reference)
  "timestamp": { "$date": "2025-09-16T23:42:00Z" },
  "timezone": "Asia/Kolkata",
  "text_content": "I was back in my college library...",
  "audio_url": null,
  "audio_transcript": null,
  "language": "en",
  "analysis": {
     "status": "complete",
     "model": "vertex-palm2-chat-2025-09",
     "generated_at": { "$date": "2025-09-17T00:02:00Z" },
     "summary": "This dream suggests academic stress...",
     "emotions": {"anxiety": 0.78, "nostalgia": 0.45},
     "sentiment_score": -0.35,
     "themes": ["exams", "identity"],
     "symbols": [{"symbol": "blank books", "confidence": 0.92, "explanation": "..." }],
     "risk_flags": {"self_harm":"none","suicide":"none","violence":false}
  },
  "share_policy": {"shareable": true, "forum_anonymous": true, "allow_research": false},
  "status": "analyzed",
  "created_at": { "$date": "2025-09-17T00:00:00Z" }
}