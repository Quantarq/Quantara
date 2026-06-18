import os
import uuid
import subprocess
import sys

import psycopg2


def _run_alembic(args, env, cwd):
    cmd = [sys.executable, "-m", "alembic"] + args
    subprocess.run(cmd, cwd=cwd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def test_migration_roundtrip():
    # Project root (quantara)
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    env = os.environ.copy()
    db_host = env.get("DB_HOST", "localhost")
    db_port = env.get("DB_PORT", "5432")
    db_user = env.get("DB_USER", "postgres")
    db_password = env.get("DB_PASSWORD", "password")

    test_db = f"quantara_test_migrations_{uuid.uuid4().hex[:8]}"

    # Create ephemeral test database
    admin_conn = psycopg2.connect(host=db_host, port=db_port, user=db_user, password=db_password, dbname="postgres")
    admin_conn.autocommit = True
    cur = admin_conn.cursor()
    cur.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
    cur.execute(f'CREATE DATABASE "{test_db}"')
    cur.close()
    admin_conn.close()

    env["DB_NAME"] = test_db

    try:
        # Upgrade to head
        _run_alembic(["-c", "web_app/alembic.ini", "upgrade", "head"], env, project_dir)

        # Downgrade back to base
        _run_alembic(["-c", "web_app/alembic.ini", "downgrade", "base"], env, project_dir)
    finally:
        # Ensure database is dropped
        admin_conn = psycopg2.connect(host=db_host, port=db_port, user=db_user, password=db_password, dbname="postgres")
        admin_conn.autocommit = True
        cur = admin_conn.cursor()
        cur.execute(
            """
            SELECT pg_terminate_backend(pid) FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid();
            """,
            (test_db,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
        cur.close()
        admin_conn.close()
