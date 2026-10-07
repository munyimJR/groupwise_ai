"""Database engine/session setup. SQLite locally, Supabase Postgres in production."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _normalize_url(url: str) -> str:
    # Supabase hands out postgres:// / postgresql:// URLs; use the psycopg 3 driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def make_engine(url: str) -> Engine:
    url = _normalize_url(url)
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - driver hook
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=15000")
            cur.close()

        return eng
    # prepare_threshold=None keeps psycopg compatible with Supabase's transaction pooler (PgBouncer).
    eng = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
        connect_args={"prepare_threshold": None},
    )
    schema = get_settings().db_schema
    if schema:
        if not schema.replace("_", "").isalnum():
            raise ValueError("DB_SCHEMA may only contain letters, digits and underscores.")

        @event.listens_for(eng, "connect")
        def _search_path(dbapi_conn, _):  # pragma: no cover - driver hook
            with dbapi_conn.cursor() as cur:
                cur.execute(f"SET search_path TO {schema}")
            dbapi_conn.commit()

    return eng


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------------------------------------------- row-level security
# The API (server-side, table owner) is the only write path: it enforces the ledger rules. Supabase also exposes
# tables to browsers through its Data API with the public anon key, so the database itself must refuse anything
# the API would refuse. Policy: anon gets nothing; a signed-in user may only READ rows of groups they're an active
# member of (plus their own profile and notifications); nobody but the API can write; operational and security
# tables (audit log, tokens, rate limits, outbox, experiment data, wallet internals) are API-only.
MEMBER_READABLE = {  # table -> SQL condition for a signed-in member (SELECT only)
    "groups": "gw_is_member(id)",
    "group_members": "gw_is_member(group_id)",
    "expenses": "gw_is_member(group_id)",
    "settlements": "gw_is_member(group_id)",
    "goals": "gw_is_member(group_id)",
    "payment_requests": "gw_is_member(group_id)",
    "expense_splits": "exists (select 1 from expenses e where e.id = expense_id and gw_is_member(e.group_id))",
    "goal_contributions": "exists (select 1 from goals g where g.id = goal_id and gw_is_member(g.group_id))",
    "users": "id = (select auth.uid())::text",
    "notifications": "user_id = (select auth.uid())::text",
}


def rls_statements(schema: str, supabase_roles: bool = True) -> list[str]:
    """SQL that enables RLS everywhere and, on Supabase, installs the explicit policies above."""
    tables = [t.name for t in Base.metadata.sorted_tables]
    out = [f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY' for t in tables]
    if not supabase_roles:
        return out
    out.append(f"""CREATE OR REPLACE FUNCTION "{schema}".gw_is_member(gid text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = "{schema}", pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM group_members m WHERE m.group_id = gid
                 AND m.user_id = (SELECT auth.uid())::text AND m.status = 'active')
$$""")
    out.append(f'REVOKE ALL ON FUNCTION "{schema}".gw_is_member(text) FROM PUBLIC')
    out.append(f'GRANT EXECUTE ON FUNCTION "{schema}".gw_is_member(text) TO authenticated')
    for t in tables:
        out.append(f'REVOKE ALL ON "{t}" FROM anon')
        out.append(f'DROP POLICY IF EXISTS gw_member_read ON "{t}"')
        if t in MEMBER_READABLE:
            out.append(f'REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON "{t}" FROM authenticated')
            out.append(f'CREATE POLICY gw_member_read ON "{t}" FOR SELECT TO authenticated USING ({MEMBER_READABLE[t]})')
        else:
            out.append(f'REVOKE ALL ON "{t}" FROM authenticated')
    return out


def _has_supabase_roles(conn) -> bool:
    return bool(conn.execute(text(
        "select exists (select 1 from pg_roles where rolname = 'authenticated') "
        "and exists (select 1 from pg_roles where rolname = 'anon') "
        "and exists (select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where n.nspname = 'auth' and p.proname = 'uid')")).scalar())


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            schema = conn.execute(text("select current_schema()")).scalar()
            for stmt in rls_statements(schema, _has_supabase_roles(conn)):
                conn.execute(text(stmt))
