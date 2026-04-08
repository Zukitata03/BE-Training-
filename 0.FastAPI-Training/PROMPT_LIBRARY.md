# Prompt Library — Copy-Paste for Each Learning Day

Each prompt is designed to produce production-quality output. Review the result against the checklists in TRAINING_GUIDE.md.

---

## Day 1: Scaffold + Architecture Review

```
Build a FastAPI CRUD module for a "Project" resource following this architecture:

Structure:
- Route file: app/api/v1/projects.py
- Service file: app/services/project_service.py  
- Model file: app/models/project.py
- Schema file: app/schemas/project.py

Project fields: id, name, description, owner_id (FK to users), status (enum: active/archived), created_at, updated_at

Requirements:
1. Full CRUD: GET /, GET /{id}, POST /, PUT /{id}, DELETE /{id}
2. Ownership enforcement — users can only access their own projects
3. Pagination on GET / (page + page_size params)
4. Pydantic v2 schemas: ProjectCreate, ProjectUpdate, ProjectResponse
5. SQLAlchemy 2.0 model with Mapped types
6. Service layer with real DB queries (no fake returns)
7. Proper error handling: 404 for not found, 403 for wrong owner
8. All endpoints require authentication (use Depends(get_current_active_user))
9. Type hints on everything
10. No business logic in routes — delegate to service

Use the existing patterns from this codebase as reference:
- app/core/database.py for get_db dependency
- app/core/security.py for get_current_active_user
- app/services/book_service.py as a pattern for service structure
```

---

## Day 2: Auth Enhancement — Role-Based Access Control

```
Add role-based access control to this FastAPI auth system.

Changes needed:
1. Update User model: add `role` column (enum: "user", "admin"), default "user"
2. Update UserCreate schema: add optional `role` field (only admins can set it)
3. Create a new dependency: `require_role(role: str)` in app/core/security.py
   - Checks if current_user.role matches the required role
   - Raises 403 Forbidden if not
4. Update register endpoint: new users always get "user" role (ignore role in payload)
5. Add a new endpoint: GET /api/v1/users (admin only) — list all users with pagination
6. Add a new endpoint: PUT /api/v1/users/{id}/role (admin only) — change a user's role

Requirements:
- Use SQLAlchemy 2.0 patterns
- Pydantic v2 schemas
- Service layer for all business logic
- Proper error handling
- Type hints everywhere
- No duplicate code — reuse existing patterns
```

---

## Day 3: Background Tasks + Notifications

```
Add a notification system to this FastAPI app using both FastAPI BackgroundTasks and Celery.

Part 1 — FastAPI BackgroundTasks (simple, fire-and-forget):
1. Create app/services/notification_service.py
2. When a user registers, trigger a BackgroundTask that logs "New user registered: {email}"
3. When a book is created, trigger a BackgroundTask that logs "New book created: {title} by user {id}"

Part 2 — Celery Task (heavy, retryable):
1. Create a Celery task: `analyze_user_activity(user_id: int)`
   - Queries all books by that user
   - Calculates: total books, average title length, most common author
   - Returns a dict with the stats
   - Has max_retries=3, retry_delay=5 seconds
2. Add a new endpoint: POST /api/v1/books/{id}/analyze
   - Triggers the Celery task asynchronously
   - Returns immediately with {"task_id": "...", "status": "processing"}
3. Add a new endpoint: GET /api/v1/tasks/{task_id}
   - Returns the task result if complete, or {"status": "processing"} if not

Requirements:
- Celery app is already configured in app/tasks/celery_app.py
- Use the existing Redis broker
- Proper error handling in all endpoints
- Type hints everywhere
```

---

## Day 4: Blockchain Integration + Scaling

```
Enhance the blockchain module in this FastAPI app.

Part 1 — Event Decoding:
1. Update app/services/blockchain_service.py to properly decode events using contract ABIs
2. Add a method: `decode_event(log: dict, abi: list) -> dict`
   - Takes a raw log from eth_getLogs and an ABI
   - Returns decoded event data with named fields
3. Add a method: `get_events_by_contract(contract_address: str, limit: int = 50)`
   - Queries the blockchain_events table
   - Returns paginated results

Part 2 — Transaction Monitoring:
1. Add a Celery task: `monitor_large_transactions(min_value_eth: float = 10.0)`
   - Fetches the latest 100 blocks
   - Finds transactions with value > min_value_eth
   - Stores them in a new model: LargeTransaction (id, tx_hash, from_address, to_address, value_eth, block_number, detected_at)
   - Runs every 60 seconds via Celery Beat

Part 3 — API:
1. Add GET /api/v1/blockchain/large-transactions?min_value=10&page=1
2. Add POST /api/v1/blockchain/monitor (admin only) — manually trigger the monitor task

Requirements:
- Use web3.py for blockchain interaction
- SQLAlchemy 2.0 for the new model
- Celery for scheduled tasks
- Proper pagination on all list endpoints
- Auth required for all endpoints
```

---

## Interview Prep Prompts

```
I'm studying this FastAPI codebase for a backend engineering interview. Quiz me:

1. Generate 10 technical questions based on the patterns in this codebase
2. For each question, provide:
   - The question
   - What a good answer looks like (3-4 sentences)
   - What a great answer looks like (includes tradeoffs, alternatives)
3. Focus on: architecture decisions, security, async patterns, database design, API design
4. After each question, wait for my answer before showing the solution
```

```
Review this FastAPI codebase for security vulnerabilities. For each issue found:
1. Describe the vulnerability
2. Show the exact code location
3. Explain the exploit scenario
4. Provide the fix
5. Rate severity: Critical / High / Medium / Low

Focus on: authentication, authorization, input validation, secret management, SQL injection, XSS, rate limiting.
```

```
How would you scale this FastAPI API to handle 10,000 requests/minute?

Provide a step-by-step plan covering:
1. Database: connection pooling, read replicas, caching strategy
2. Application: horizontal scaling, load balancing, async optimization
3. Infrastructure: CDN, rate limiting, monitoring, alerting
4. Blockchain: event indexing optimization, node selection, retry strategies

For each recommendation, explain the tradeoff and when it becomes necessary.
```
