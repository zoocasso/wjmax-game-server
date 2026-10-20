"""Database engine and table definitions (SQLAlchemy Core).

The tables are declared here instead of reflected at import time, so the app starts even when the
database is briefly unreachable and the schema lives in the code (see schema.sql for the DDL).
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Engine,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection

from app.config import get_settings

metadata = MetaData()

user_tb = Table(
    "user_tb",
    metadata,
    Column("device_id", String(64), primary_key=True),
    Column("insert_date", DateTime, nullable=False),  # first time the device was seen
)

# one row per chart: every song has CHARTS_PER_SONG consecutive keys that share its name
music_tb = Table(
    "music_tb",
    metadata,
    Column("music_key", Integer, primary_key=True),
    Column("name", String(100), nullable=False, index=True),
)

# one row per report a device sends; report_id is the client's id for the report (it lets a retry
# be recognised) or a UUID the server made up when the client sent none
report_tb = Table(
    "report_tb",
    metadata,
    Column("device_id", String(64), ForeignKey("user_tb.device_id"), primary_key=True),
    Column("report_id", String(64), primary_key=True),
    # microseconds, so the snapshots of one device sort even when two arrive in the same second
    Column("reported_at", DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False),
)

# play counts are appended as snapshots, one row per chart per report
playcount_tb = Table(
    "playcount_tb",
    metadata,
    # SQLite only auto-increments an INTEGER primary key
    Column("id", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("device_id", String(64), nullable=False),
    Column("report_id", String(64), nullable=False),
    Column("music_key", Integer, nullable=False),
    Column("count", Integer, nullable=False),
    ForeignKeyConstraint(["device_id", "report_id"], ["report_tb.device_id", "report_tb.report_id"]),
    Index("ix_playcount_tb_report", "device_id", "report_id"),
)


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping replaces connections RDS has closed while idle
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800)


def get_connection() -> Iterator[Connection]:
    """FastAPI dependency: one pooled connection per request; the endpoint opens the transaction."""
    with get_engine().connect() as conn:
        yield conn
