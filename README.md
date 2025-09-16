# Project Setup

run the command:

`uv run fastapi dev main.py`

That's it :) 



````
better-yuu-backend/          # Project root
│
├── app/                     # Application package
│   ├── __init__.py          # Makes app a Python package
│   ├── main.py              # Entry point: create FastAPI app instance here
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   └── endpoints.py     # One or more route modules
│   ├── core/                # Core settings/configuration
│   │   ├── __init__.py
│   │   └── config.py        # Configurations like env vars, constants
│   ├── models/              # Pydantic models, DB models
│   │   ├── __init__.py
│   │   └── item.py          # Example model
│   ├── services/            # Business logic / service layer
│   │   ├── __init__.py
│   │   └── some_service.py
│   ├── db/                  # Database related files
│   │   ├── __init__.py
│   │   └── session.py       # DB session, engine setup
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── helpers.py
│
├── tests/                   # Tests for your app
│   ├── __init__.py
│   └── test_main.py
│
├── pyproject.toml           # Project metadata, dependencies
├── README.md
├── requirements.txt         # Optional, if you still use pip requirements
└── .env                     # Environment variables file (optional)
