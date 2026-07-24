from pathlib import Path


ALERT_SOURCE = Path("quantara/web_app/contract_tools/mixins/alert.py")


def test_alert_sweep_uses_bounded_concurrency_and_timeout():
    source = ALERT_SOURCE.read_text(encoding="utf-8")

    assert "asyncio.Semaphore(ALERT_CONCURRENCY_LIMIT)" in source
    assert 'HEALTH_RATIO_ALERT_CONCURRENCY", "16"' in source
    assert "asyncio.wait_for(" in source
    assert "timeout=ALERT_TASK_TIMEOUT_SECONDS" in source
    assert "asyncio.gather(*tasks, return_exceptions=True)" in source


def test_alert_sweep_records_success_and_failure_metrics():
    source = ALERT_SOURCE.read_text(encoding="utf-8")

    assert "health_ratio_alert_sweep_results_total" in source
    assert "ALERT_SWEEP_COUNTER.labels(outcome=\"success\").inc(success_count)" in source
    assert "ALERT_SWEEP_COUNTER.labels(outcome=\"failure\").inc(failure_count)" in source
    assert "health_ratio_alert_sweep_summary" in source