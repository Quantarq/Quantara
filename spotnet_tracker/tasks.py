"""
This module contains Celery tasks for the application.

It imports the logging module to facilitate logging operations and the
Celery app instance from the `celery_config` module.

Tasks:
- test_task: A simple test task that logs a confirmation message.
"""

import logging

from .celery_config import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@app.task(name="test_task")
def test_task() -> None:
    """
    A task cybled to test that all is working as expected.
    :return: None
    """
    # TODO: remove on production
    logger.info("Running test_task. All is working as expected.")
