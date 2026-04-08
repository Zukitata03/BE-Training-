# Agent-Driven Backend Training Guide

**Target:** Junior/Fresher BE Engineer in 4 days (~1 hour/day)
**Prerequisites:** You already know Python, smart contracts, and have worked with BE devs.

---

## How This Works

You don't write boilerplate. AI agents do. Your job is to:
1. **Direct** agents with precise prompts (use PROMPT_LIBRARY.md)
2. **Review** their output against the checklists below
3. **Learn** by understanding WHY the code is structured this way

The codebase in `TrainingAPI/` is your reference. Read it first, then use agents to build similar things.

---

## Day 1: Architecture + FastAPI Basics (1 hour)

### Read first (15 min)
1. `TrainingAPI/app/main.py` — How the app factory pattern works
2. `TrainingAPI/app/api/v1/router.py` — How routers are composed
3. `TrainingAPI/app/core/database.py` — Why engine is lazy-initialized
4. `TrainingAPI/app/services/book_service.py` — Why business logic lives here, not in routes

### Key concepts to understand
- **App Factory**: `create_app()` function that builds the FastAPI instance. Why? Testing, multiple instances, clean startup.
- **Service Layer**: Routes validate input → call service → return response. Services contain ALL business logic.
- **Dependency Injection**: `Depends(get_db)` gives each request its own DB session. No global state.
- **Async**: `async def` endpoints don't block. The event loop handles other requests while waiting for DB.

### Agent exercise (30 min)
Use the Day 1 prompt from PROMPT_LIBRARY.md. Ask an agent to scaffold a similar CRUD for a "Project" resource.

### INTEGRATE & RUN (15 min) — DO NOT SKIP
1.  **Place files**: Save agent's code into `app/api/v1/`, `app/services/`, and `app/models/`.
2.  **Wire it up**: Open `app/api/v1/router.py` and add the new router:
    ```python
    from . import projects
    router.include_router(projects.router, prefix="/projects", tags=["projects"])
    ```
3.  **Run**: `uvicorn TrainingAPI.app.main:create_app --factory --reload`
4.  **Test**: Go to `http://localhost:8000/docs`. Try `POST /projects`.
    *   *If it crashes:* Read the error log. Fix the import or syntax. This is part of the job.

### Review checklist (15 min)
When reviewing agent-generated code, check:
- [x] Routes are thin (< 10 lines each)
- [x] Business logic is in `services/`, not routes
- [x] DB session uses `Depends(get_db)` pattern
- [x] Pydantic schemas separate input (Create/Update) from output (Response)
- [x] No hardcoded secrets or config values
- [x] Type hints on all function signatures

---

## Day 2: Authentication (1 hour)

### Read first (15 min)
1. `TrainingAPI/app/core/security.py` — Password hashing, JWT, `get_current_user`
2. `TrainingAPI/app/services/auth_service.py` — Register + login with real DB queries
3. `TrainingAPI/app/api/v1/auth.py` — Thin auth routes
4. `TrainingAPI/app/models/user.py` — User model structure

### Key concepts to understand
- **Password hashing**: `bcrypt` — one-way. You can NEVER recover a password from its hash. You verify by hashing the input and comparing.
- **JWT**: JSON Web Token. Contains user info + expiration. Signed with a secret key. Stateless — no DB lookup needed to validate.
- **Access vs Refresh token**: Access = short-lived (15 min), used for every request. Refresh = long-lived (7 days), used only to get new access tokens.
- **OAuth2PasswordBearer**: FastAPI's built-in auth dependency. Extracts `Bearer <token>` from the `Authorization` header.

### Agent exercise (30 min)
Use the Day 2 prompt from PROMPT_LIBRARY.md. Add role-based access control (admin/user roles).

### Review checklist (15 min)
- [x] Passwords are NEVER stored or logged in plaintext
- [x] JWT secret comes from environment, not hardcoded
- [x] `get_current_user` raises 401, not 500, on invalid token
- [x] Token has `type` claim to distinguish access vs refresh
- [x] Registration checks for duplicate email (409 Conflict)
- [x] Login returns 401 for wrong password, not 500

---

## Day 3: Background Tasks + Cron Jobs (1 hour)

### Read first (15 min)
1. `TrainingAPI/app/tasks/celery_app.py` — Celery configuration
2. `TrainingAPI/app/tasks/blockchain_tasks.py` — A scheduled task that polls blockchain
3. `TrainingAPI/docker-compose.yml` — How celery-worker and celery-beat are separate services

### Key concepts to understand
- **BackgroundTasks (FastAPI built-in)**: Fire-and-forget. Runs after the HTTP response is sent. Good for: send email, log event, trigger webhook.
- **Celery**: Separate worker process. Runs tasks from a queue (Redis). Good for: heavy computation, retries, scheduled tasks.
- **Celery Beat**: The scheduler. Like a cron job but Python-native. Runs tasks on a schedule (e.g., every 30 seconds).
- **Cron job definition**: A task that runs automatically at specified intervals. In Linux: `*/30 * * * * command`. In Celery: `beat_schedule` config.

**Real-world blockchain examples:**
- Every 30s: Poll `eth_getLogs` for new events
- Every 5min: Aggregate daily trading volume
- Every midnight: Clean up expired JWT tokens from DB
- On-demand: Index a specific contract's history

### Agent exercise (30 min)
Use the Day 3 prompt from PROMPT_LIBRARY.md. Add a task that sends a notification when a large transaction is detected.

### Review checklist (15 min)
- [ ] Celery tasks are idempotent (safe to run multiple times)
- [ ] Tasks have `max_retries` to handle transient failures
- [ ] No blocking code in FastAPI endpoints (use BackgroundTasks or Celery)
- [ ] Task failures are logged, not silently swallowed
- [ ] Beat schedule uses reasonable intervals (not every 1 second)

---

## Day 4: Blockchain Integration + Interview Prep (1 hour)

### Read first (15 min)
1. `TrainingAPI/app/services/blockchain_service.py` — web3.py integration
2. `TrainingAPI/app/api/v1/blockchain.py` — Endpoints for event indexing
3. `TrainingAPI/app/models/blockchain_event.py` — How on-chain events are stored

### Key concepts to understand
- **web3.py in backend**: Connects to an EVM node via HTTP/RPC. Used to read chain state, fetch logs, send transactions.
- **Event indexing**: `eth_getLogs` returns raw logs. You decode them using the contract ABI, then store in your DB for fast querying.
- **Why store events in DB?** Chain queries are slow. A local DB lets you query "all Swap events for this contract" in milliseconds instead of scanning thousands of blocks.

### Interview prep (45 min)
Ask an AI agent these questions. Answer them yourself first, then compare:

1. **What's the difference between FastAPI's BackgroundTasks and Celery?**
2. **How does JWT authentication work? Walk me through the flow.**
3. **Why use a service layer instead of putting logic in routes?**
4. **What happens when two users try to register with the same email?**
5. **How would you scale this API to handle 10,000 requests/minute?**
6. **What's the difference between synchronous and asynchronous database operations?**
7. **How do you prevent SQL injection in this codebase?**
8. **What's the purpose of `Depends()` in FastAPI?**
9. **How would you add rate limiting to this API?**
10. **Explain the difference between access tokens and refresh tokens.**

---

## Architecture Explained

### Why this structure?

```
app/
├── api/v1/          # Routes — thin, only validate + delegate
├── core/            # Config, security, database — infrastructure
├── models/          # SQLAlchemy ORM models — data shape
├── schemas/         # Pydantic schemas — API input/output contracts
├── services/        # Business logic — the "brain" of your app
├── tasks/           # Celery background tasks — async work
├── middleware/      # Request/response interceptors
└── dependencies/    # FastAPI Depends() helpers
```

**Routes → Services → Models** is the standard production pattern. Routes are the door, services are the workers, models are the filing cabinet.

### Why separate schemas from models?
- **Models** = database shape (SQLAlchemy columns)
- **Schemas** = API shape (Pydantic validation)
- A User model has `hashed_password`. A UserResponse schema should NEVER expose it.
- A BookCreate schema requires `title` and `author`. The Book model also has `owner_id` and `created_at` which the client doesn't send.

### Why async?
Python's GIL means only one thread runs at a time. But `async` lets you wait for I/O (DB, HTTP, Redis) without blocking other requests. A sync endpoint handling a slow DB query blocks ALL other requests. An async one doesn't.

---

## Running the Project

```bash
# Local dev (no Docker)
cd 0.FastAPI-Training/TrainingAPI
cp .env.example .env
pip install -r requirements.txt
uvicorn TrainingAPI.app.main:create_app --factory --reload

# With Docker
docker-compose up --build
```

---

## Syntax Decoder (Read This First)

You know Python, but you don't know **FastAPI/SQLAlchemy/Pydantic** syntax yet. This section translates the "magic" methods you'll see in the code.

### 1. Database (SQLAlchemy Async)

| Code | Plain English |
| :--- | :--- |
| `db: AsyncSession = Depends(get_db)` | "Give me a fresh database connection for this request. Close it when done." |
| `await db.flush()` | "Send these changes to the database **now** so I can get the ID, but **don't save permanently yet**." |
| `await db.commit()` | "Save everything permanently. This is the 'Save' button." |
| `await db.rollback()` | "Undo everything since the last commit. Something went wrong." |
| `await db.refresh(obj)` | "Go back to the DB and update this object with the latest data (e.g., auto-generated IDs)." |
| `select(Model).where(...)` | "Build a SQL query: `SELECT * FROM table WHERE ...`" |
| `result.scalar_one()` | "Run the query. I expect exactly **one** result. Error if 0 or 2+." |
| `result.scalar_one_or_none()` | "Run the query. I expect **zero or one** result. Return `None` if not found." |

### 2. Validation (Pydantic)

| Code | Plain English |
| :--- | :--- |
| `model_validate(obj)` | "Turn this Database Object into a Pydantic Schema (for the API response)." |
| `model_dump()` | "Turn this Pydantic Schema into a plain Python Dictionary." |
| `model_dump(exclude_unset=True)` | "Turn into dict, but **only include fields the user actually sent** (for partial updates)." |
| `Field(...)` | "This field is required." |
| `Field(default=None)` | "This field is optional." |

### 3. FastAPI Patterns

| Code | Plain English |
| :--- | :--- |
| `Depends(function)` | "Run this function *before* my endpoint. Use its return value." |
| `HTTPException(status_code=404)` | "Stop everything. Return a 404 error JSON to the user immediately." |
| `response_model=BookResponse` | "Take whatever I return, validate it against `BookResponse`, and hide any extra fields." |
| `Annotated[int, Query(...)]` | "This is a URL parameter (e.g., `?page=1`). Validate it with these rules." |
| `APIRouter()` | "A mini-app. I group related routes (like all 'Books' routes) here." |

### 4. Models (SQLAlchemy 2.0)

| Code | Plain English |
| :--- | :--- |
| `Mapped[str]` | "This column holds a string. Python knows the type." |
| `mapped_column(...)` | "Define the database column rules (nullable, unique, etc)." |
| `ForeignKey("users.id")` | "This column links to the `id` column in the `users` table." |

---

## How to Read the Code (The "3-Pass" Method)

Don't try to understand every line at once. Read each file 3 times:

1.  **Pass 1 (The "What"):** Look at the **function names** and **routes**.
    *   *Example:* `POST /books` calls `create_book`. It takes `BookCreate` and returns `BookResponse`.
    *   *Goal:* Understand what the endpoint *does*, not how.
2.  **Pass 2 (The "How"):** Look at the **Service Layer**.
    *   *Example:* `create_book` calls `db.add()`, then `db.flush()`.
    *   *Goal:* Use the **Syntax Decoder** above to understand the DB calls.
3.  **Pass 3 (The "Why"):** Look at the **Architecture**.
    *   *Example:* Why is `db` passed as an argument? Why is `owner_id` taken from `current_user`?
    *   *Goal:* Understand the design decisions.

---

## MongoDB / Beanie Cheat Sheet (For Your Company)

This training uses SQLAlchemy (SQL). Your company uses MongoDB. The **architecture** is identical — only the database layer changes.

**Install:** `pip install beanie motor`

### 1. Database Setup

| SQLAlchemy (Training) | Beanie (Your Company) |
|---|---|
| `core/database.py` | `core/mongodb.py` |
| `create_async_engine()` | `init_beanie()` |
| `AsyncSession` | Motor client (auto-managed) |

```python
# core/mongodb.py
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from ..models.user import User
from ..models.book import Book

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["training_db"]

async def init_db():
    await init_beanie(database=db, document_models=[User, Book])

async def close_db():
    client.close()
```

### 2. Model Definition

| SQLAlchemy (Training) | Beanie (Your Company) |
|---|---|
| `class User(Base)` | `class User(Document)` |
| `Mapped[str] = mapped_column(...)` | `email: str` (Pydantic fields) |
| `ForeignKey("users.id")` | `Link[User]` or manual `owner_id: PydanticObjectId` |

```python
# models/user.py
from beanie import Document, Indexed
from pydantic import Field

class User(Document):
    email: Indexed(str, unique=True)
    hashed_password: str
    is_active: bool = True
```

```python
# models/book.py
from beanie import Document, Link
from pydantic import Field

class Book(Document):
    title: str
    author: str
    description: str | None = None
    owner: Link["User"]  # Beanie's way of doing FK
```

### 3. CRUD Operations

| Operation | SQLAlchemy (Training) | Beanie (Your Company) |
|---|---|---|
| **Create** | `db.add(user); await db.flush()` | `await user.insert()` |
| **Read One** | `await db.execute(select(User).where(...))` | `await User.find_one(User.email == email)` |
| **Read Many** | `result.scalars().all()` | `await User.find_all().to_list()` |
| **Update** | `setattr(); await db.flush()` | `await user.save()` or `user.set()` |
| **Delete** | `await db.delete(user); await db.flush()` | `await user.delete()` |
| **Count** | `select(func.count())` | `await User.find_all().count()` |
| **Pagination** | `.offset().limit()` | `.skip().limit()` |

```python
# services/book_service.py — Beanie version
from beanie import PydanticObjectId

async def get_books(self, owner_id: PydanticObjectId, page: int = 1, page_size: int = 20):
    skip = (page - 1) * page_size
    books = await Book.find(Book.owner.id == owner_id).skip(skip).limit(page_size).to_list()
    total = await Book.find(Book.owner.id == owner_id).count()
    return books, total

async def create_book(self, payload: BookCreate, owner_id: PydanticObjectId):
    owner = await User.get(owner_id)
    book = Book(title=payload.title, author=payload.author, owner=owner)
    await book.insert()
    return book

async def get_book(self, book_id: PydanticObjectId, owner_id: PydanticObjectId):
    return await Book.find_one(Book.id == book_id, Book.owner.id == owner_id)

async def update_book(self, book_id: PydanticObjectId, owner_id: PydanticObjectId, payload: BookUpdate):
    book = await self.get_book(book_id, owner_id)
    if book is None:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)
    await book.save()
    return book

async def delete_book(self, book_id: PydanticObjectId, owner_id: PydanticObjectId):
    book = await self.get_book(book_id, owner_id)
    if book is None:
        return False
    await book.delete()
    return True
```

### 4. Auth Service — Beanie Version

```python
# services/auth_service.py — Beanie version
from beanie import PydanticObjectId
from ..models.user import User
from ..core.security import hash_password, verify_password

async def register_user(self, payload: UserCreate):
    existing = await User.find_one(User.email == payload.email)
    if existing:
        raise ValueError(f"Email {payload.email} already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    await user.insert()
    return user

async def authenticate_user(self, email: str, password: str):
    user = await User.find_one(User.email == email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
```

### 5. Security Dependency — Beanie Version

```python
# core/security.py — get_current_user with Beanie
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_token(token)
    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await User.find_one(User.email == email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

### 6. Key Differences to Remember

| Concept | SQL | MongoDB/Beanie |
|---|---|---|
| **Transactions** | `async with db.begin()` | `async with await client.start_session()` |
| **Migrations** | Alembic (required) | Not needed (schemaless), but use `migrations` for indexes |
| **Joins** | `JOIN` via relationships | `fetch_links=True` on queries, or manual lookups |
| **Indexes** | Defined in columns | `Indexed()` wrapper or `class Settings: indexes = [...]` |
| **ID Type** | `int` (auto-increment) | `PydanticObjectId` (ObjectId) |

### When to Use Which at Work

- **Use Beanie** when: Your company already uses MongoDB, data is document-shaped, you need flexible schemas.
- **Use SQL** when: You need strict data integrity, complex relationships, or are building from scratch.

**The patterns you learn here (Services, Auth, DI, Async) work identically with both.**
