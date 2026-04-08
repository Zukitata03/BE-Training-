import logging

logger = logging.getLogger(__name__)


def log_new_user_registered(email: str) -> None:
    logger.info("New user registered: %s", email)


def log_new_book_created(title: str, user_id: int) -> None:
    logger.info("New book created: %s by user %s", title, user_id)

