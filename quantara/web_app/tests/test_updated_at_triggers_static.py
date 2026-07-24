from pathlib import Path


WEB_APP = Path(__file__).resolve().parents[1]
MODELS = (WEB_APP / "db/models.py").read_text()
MIGRATION = (WEB_APP / "alembic/versions/229_updated_at_triggers.py").read_text()


def _class_body(class_name: str) -> str:
    start = MODELS.index(f"class {class_name}(Base):")
    next_class = MODELS.find("\nclass ", start + 1)
    return MODELS[start:] if next_class == -1 else MODELS[start:next_class]


def test_core_audit_models_have_updated_at_columns():
    for class_name in ("User", "Position", "AirDrop"):
        body = _class_body(class_name)
        assert "updated_at = Column" in body
        assert "onupdate=func.now()" in body


def test_migration_adds_missing_updated_at_columns():
    assert 'for table_name in ("user", "position", "airdrop"):' in MIGRATION
    for table_name in ("user", "position", "airdrop"):
        assert f'op.add_column(\n            table_name,' in MIGRATION
        assert table_name in MIGRATION
    assert 'op.drop_column(table_name, "updated_at")' in MIGRATION


def test_migration_installs_triggers_for_all_updated_at_tables():
    assert "CREATE OR REPLACE FUNCTION set_updated_at()" in MIGRATION
    assert "NEW.updated_at = NOW();" in MIGRATION
    for table_name in (
        "user",
        "position",
        "airdrop",
        "telegram_user",
        "vault",
        "transaction",
        "extra_deposits",
        "event_outbox",
    ):
        assert f'"{table_name}"' in MIGRATION
    assert "CREATE TRIGGER" in MIGRATION
    assert "EXECUTE FUNCTION set_updated_at();" in MIGRATION