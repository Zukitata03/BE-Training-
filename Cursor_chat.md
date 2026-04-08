# Notification system with FastAPI and Celery
_Exported on 4/8/2026 at 14:46:31 GMT+7 from Cursor (3.0.13)_

---

**User**

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

---

**Cursor**

Got it. I’m going to (1) inspect the existing FastAPI app structure and current user/book endpoints, (2) add a small `notification_service` used by `BackgroundTasks` for register + book-create, (3) add the Celery task `analyze_user_activity` and wire up the two new API endpoints to trigger it and poll results, then (4) run a quick import/type check pass (and lints if configured) to make sure everything still boots cleanly.

I’ve found the relevant modules already exist (`api/v1/auth.py`, `api/v1/books.py`, and `tasks/celery_app.py`). Next I’ll read the current register + book-create flows and the existing Celery setup so we can hook notifications and add the new analysis task/endpoints without breaking the project’s service-layer structure.

Key constraint I found: the Celery worker in `docker-compose.yml` starts with `-A TrainingAPI.app.tasks.blockchain_tasks`, so any new Celery task must be imported/registered when that module loads. Next I’ll add the new `analyze_user_activity` task in its own module and import it from `blockchain_tasks.py` (side-effect registration), then wire the two new endpoints plus the BackgroundTasks notifications.

BackgroundTasks notifications are now wired into register + book-create, and `/books/{book_id}/analyze` is stubbed to enqueue the Celery job. Next I’ll add the actual Celery task implementation (sync DB query + stats), ensure it’s discoverable by the existing Celery worker entrypoint, and add the `/tasks/{task_id}` polling endpoint under the v1 router.

One important fix to ensure this actually runs: the current `docker-compose.yml` starts Celery with `-A ...blockchain_tasks`, but your project’s real Celery configuration lives in `app/tasks/celery_app.py` (and that’s also what the new API endpoints use to enqueue/poll tasks). Next I’ll update the compose worker/beat commands to use that configured app so both the existing scheduled blockchain poll and the new user-activity analysis task run under the same Celery app.

All edited files are lint-clean. Next I’ll run the existing test suite (at least the book/auth tests) to confirm the new endpoints/imports don’t break startup, and I’ll sanity-check that the Celery task name used by `/books/{book_id}/analyze` matches what Celery registers.

### What I added

#### Part 1 — FastAPI `BackgroundTasks` (fire-and-forget logging)
- **New service**: `TrainingAPI/app/services/notification_service.py`
  - `log_new_user_registered(email: str) -> None`
  - `log_new_book_created(title: str, user_id: int) -> None`
- **User register** (`POST /api/v1/auth/register`)
  - Now schedules a background task to log: **`New user registered: {email}`**
- **Book create** (`POST /api/v1/books/`)
  - Now schedules a background task to log: **`New book created: {title} by user {id}`**

#### Part 2 — Celery task + endpoints (heavy/retryable)
- **New Celery task module**: `TrainingAPI/app/tasks/user_activity_tasks.py`
  - Task: `analyze_user_activity(user_id: int)`
  - Computes:
    - `total_books`
    - `avg_title_length`
    - `most_common_author`
  - Configured with **`max_retries=3`** and **`default_retry_delay=5`**
- **New endpoint**: `POST /api/v1/books/{id}/analyze`
  - Verifies the book exists **and belongs to the current user**
  - Enqueues Celery task asynchronously
  - Returns immediately: `{"task_id": "...", "status": "processing"}`
- **New endpoint**: `GET /api/v1/tasks/{task_id}`
  - If not ready: `{"status": "processing"}`
  - If success: `{"status": "completed", "result": {...}}`
  - If failed: `{"status": "failed", "error": "..."}`

### Celery wiring (important)
- Updated `TrainingAPI/app/tasks/celery_app.py` to **include**:
  - `TrainingAPI.app.tasks.blockchain_tasks`
  - `TrainingAPI.app.tasks.user_activity_tasks`
- Updated `TrainingAPI/docker-compose.yml` so `celery-worker` and `celery-beat` run the configured app:
  - `celery -A TrainingAPI.app.tasks.celery_app.celery_app ...`

### Files changed/added
- **Added** `TrainingAPI/app/services/notification_service.py`
- **Updated** `TrainingAPI/app/api/v1/auth.py`
- **Updated** `TrainingAPI/app/api/v1/books.py`
- **Added** `TrainingAPI/app/tasks/user_activity_tasks.py`
- **Updated** `TrainingAPI/app/tasks/celery_app.py`
- **Updated** `TrainingAPI/app/tasks/blockchain_tasks.py`
- **Added** `TrainingAPI/app/api/v1/tasks.py`
- **Updated** `TrainingAPI/app/api/v1/router.py`
- **Updated** `TrainingAPI/docker-compose.yml`

---

**User**

Add a task that sends a notification when a large transaction is detected. 


---

**Cursor**

I’ll first inspect the existing blockchain service and models to see how transactions/events are represented, then I’ll add a Celery task that evaluates each event for “large transaction” criteria and triggers a notification (likely via logging) when detected, wiring it into the existing Celery setup.

I’ve inspected your existing blockchain service/model and Celery blockchain task so the new “large transaction” task fits in cleanly. Next I’ll add a Celery task that scans recent `BlockchainEvent` records, flags large ones, sends a notification via logging, and wire it into the existing Celery app (optionally adding it to the beat schedule if you want it to run periodically).

### Added “large transaction” notification task

- **New Celery task** in `app/tasks/blockchain_tasks.py`:
  - `notify_large_transactions(limit: int = 100) -> int`
  - Uses a sync DB session to load up to `limit` recent `BlockchainEvent` rows.
  - Extracts an `amount` from `event.data` (supports:
    - dicts with `amount` or `value` fields
    - numeric strings
    - hex strings like `"0x..."` converted to an integer).
  - Compares against `LARGE_TX_THRESHOLD = 10**18` (example “large” threshold).
  - For each event over the threshold, logs a notification:
    - **`"Large transaction detected: chain=%s tx_hash=%s amount=%s"`**
  - Returns the count of large transactions it notified about.
  - Configured with `@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)` for retries.

- **Helper + logging**:
  - `logger = logging.getLogger(__name__)`
  - `_extract_amount(data: Any) -> float | None` to parse the amount from different `data` formats.

- **Scheduled via Celery Beat** (so it runs automatically):
  - In `app/tasks/celery_app.py` `beat_schedule` now includes:
    - `"notify-large-transactions"` → task `"TrainingAPI.app.tasks.blockchain_tasks.notify_large_transactions"` every `60.0` seconds with `args=(100,)` (scan latest 100 events).

---

**User**

okay so today checklist is 
@TRAINING_GUIDE.md (107-113) 
how do i check this?

---

**Cursor**

To check `TRAINING_GUIDE.md` (Day 3 checklist lines 107–113), do it directly against the code that was changed/added. Here’s a practical “how to verify” for each bullet in *this repo*.

1. `Celery tasks are idempotent (safe to run multiple times)`
   - Search for your Celery tasks and check whether they *write external state* in a way that would duplicate work.
   - In your case:
     - `poll_events()` *is* idempotent-ish because `store_events()` skips duplicates by `(tx_hash, block_number)` before inserting.
     - `notify_large_transactions()` currently just **logs** alerts after scanning recent events; if it runs again, it can log the same “large tx” again. That means it’s idempotent only in the weak sense of “won’t corrupt DB”, not “won’t repeat notifications”.

2. `Tasks have max_retries to handle transient failures`
   - In `TrainingAPI/app/tasks/blockchain_tasks.py`, confirm your tasks use:
     - `@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)`
   - Both `poll_events` and `notify_large_transactions` use `max_retries=3`.

3. `No blocking code in FastAPI endpoints (use BackgroundTasks or Celery)`
   - Check endpoints for `await asyncio.sleep(...)`, heavy CPU loops, or synchronous long-running work.
   - Your FastAPI changes for:
     - register: uses `BackgroundTasks.add_task(...)` after DB success (good)
     - book analyze enqueue: only calls Celery async enqueue and returns immediately (good)
   - For this “large tx notification” task, it’s Celery-only (no endpoint involved), so it won’t block requests.

4. `Task failures are logged, not silently swallowed`
   - Check whether tasks catch broad exceptions and either:
     - re-raise / let Celery handle it, or
     - call `self.retry(...)` (Celery will log retry/failure details)
   - Both tasks wrap errors with `raise self.retry(exc=exc)` (not swallowed), and your Celery worker/beat will emit logs.

5. `Beat schedule uses reasonable intervals (not every 1 second)`
   - Check `TrainingAPI/app/tasks/celery_app.py` → `beat_schedule`.
   - You should see the `schedule` values are not tiny:
     - `poll-blockchain-events`: `schedule: 30.0`
     - `notify-large-transactions`: `schedule: 60.0`

If you want, I can also adjust `notify_large_transactions()` to be *truly idempotent for notifications* (e.g., track alerted `tx_hash` in DB or in a Redis set), so you can confidently tick the idempotency box.

---

**User**

I don't need to run it or something to verify? 

---

**Cursor**

You *can* check most of that checklist just by reading code, but you **should** run things at least once to really verify behavior.

### What you can verify by reading

- **Idempotent-ish logic**: reading `blockchain_tasks.py` shows:
  - `poll_events` uses `store_events` which skips duplicates → DB-safe to re-run.
  - `notify_large_transactions` only reads DB + logs → no data corruption if re-run.
- **max_retries**: decorators clearly show `max_retries=3`.
- **No blocking in endpoints**: you can see endpoints only enqueue Celery / BackgroundTasks and return.
- **Failures not swallowed**: tasks call `self.retry(exc=exc)`.
- **Beat intervals**: `celery_app.conf.beat_schedule` has `30.0` and `60.0`, not 1s.

### What’s better to actually run

To be thorough, you’d usually also:

1. **Start Redis + DB** (e.g. from `TrainingAPI/`):
   ```bash
   docker compose up api redis postgres -d
   ```
2. **Start Celery worker + beat**:
   ```bash
   docker compose up celery-worker celery-beat
   ```
3. **Watch logs**:
   - Confirm `poll_events` and `notify_large_transactions` are being scheduled and retried/logged as expected.
   - Optionally trigger some blockchain events to see “Large transaction detected…” log lines.

So: reading the code is enough to *reasonably* answer the checklist, but running the stack and observing logs is the “real” verification, and what you’d do on a real job.

---

**User**

I have question that i'm running on WSL, will install docker make me consume huge size off storage?

---

**Cursor**

Yes—**Docker on WSL2 will consume a noticeable chunk of storage**, and it can grow over time, but it’s usually manageable if you keep it tidy.

### Where the space goes
- **Docker engine + Desktop app (if you use Docker Desktop)**: a few GB.
- **WSL2 Linux distro filesystem**: your Ubuntu (or other) distro already uses space.
- **Docker images/containers/volumes** (the big one):
  - Images like `postgres`, `redis`, `mongo` can easily add **multiple GB** total.
  - Volumes (like Postgres data) can grow as you use the DB.
- **WSL virtual disk (VHDX)** grows as you download/build things and doesn’t always shrink automatically.

### How to keep it from blowing up
- **Prefer Docker Desktop + WSL integration** (simpler, but uses disk).
- Periodically clean unused stuff:
  - `docker system df` (see what’s using space)
  - `docker system prune` (removes unused containers/images/networks)
  - `docker volume prune` (removes unused volumes — be careful, deletes data)

### Quick rule of thumb
If you follow this FastAPI training with Postgres/Redis/Mongo + Celery, plan for **~5–15GB** over time depending on how much you build/pull and whether you keep old images/volumes around.

If you tell me whether you’re using **Docker Desktop** or **Docker Engine inside WSL**, and roughly how much free space you have, I can give a more specific estimate and the best setup for your machine.

