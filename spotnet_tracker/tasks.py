"""
This module contains Celery tasks for the application.

It imports the logging module to facilitate logging operations and the
Celery app instance from the `celery_config` module.

Tasks:
- test_task: A simple test task that logs a confirmation message.
"""

import logging

from web_app.contract_tools.mixins.alert import AlertMixin
from web_app.contract_tools.mixins.custom_exception import HealthRatioLevelLowException

from .celery_config import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@app.task(name="test_task")
def test_task() -> None:
    """
    A task to test that all is working as expected.
    :return: None
    """
    # TODO: remove on production
    logger.info("Running test_task. All is working as expected.")


@app.task(name="check_users_health_ratio")
def check_users_health_ratio() -> None:
    """
    Background task to check health ratio levels for users with opened positions.

    :return: None
    """
    try:
        alert_mixin = AlertMixin()
        alert_mixin.check_users_health_ratio_level()
    except HealthRatioLevelLowException as e:
        logger.error(
            f"Low health ratio detected: User ID {e.user_id}, Health Ratio {e.health_ratio}"
        )
    except Exception as e:
        logger.error(f"Error in check_users_health_ratio task: {e}")
