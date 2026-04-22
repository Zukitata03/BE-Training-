from celery import Celery

from ..core.config import get_config

config = get_config()

celery_app = Celery(
    "training_tasks",
    broker=config.redis_url,
    backend=config.redis_url,
    include=[
        "app.tasks.blockchain_tasks",
        "app.tasks.user_activity_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-blockchain-events": {
            "task": "app.tasks.blockchain_tasks.poll_events",
            "schedule": 30.0,
        },
        "notify-large-transactions": {
            "task": "app.tasks.blockchain_tasks.notify_large_transactions",
            "schedule": 60.0,
            "args": (100,),
        },
        "monitor-large-transactions": {
            "task": "app.tasks.blockchain_tasks.monitor_large_transactions",
            "schedule": 60.0,
            "kwargs": {"min_value_eth": 10.0},
        },
    },
)
