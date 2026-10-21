import json
import os
import threading
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")

import anyio  # noqa: E402
import pytest  # noqa: E402
from anyio import to_thread  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, insert, inspect, make_url, select, text  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db_session  # noqa: E402
from app.db_session import REQUEST_THREADS  # noqa: E402
from app.main import MAX_BODY_BYTES, app  # noqa: E402
from app.playcount import (  # noqa: E402
    CHARTS_PER_SONG,
    MAX_COUNT,
    CountLogError,
    SongCounts,
    parse_count_log,
    save_play_counts,
)

# set in CI to run the API tests against MySQL as well; the tables then come from schema.sql
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
needs_mysql = pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs MySQL (TEST_DATABASE_URL)")


def entry(title, counts):
    return "*".join([title, *map(str, counts)])


# ---------- parsing ----------


def test_reads_the_single_quoted_log_the_client_sends():
    log = "{'playDatas': ['" + entry("Song A", range(8)) + "']}"
    [song] = parse_count_log(log)
    assert song.title == "Song A"
    assert song.counts == tuple(range(8))


def test_reads_json_too():
    log = '{"playDatas": ["' + entry("Song A", [1] * 8) + '"]}'
    assert parse_count_log(log)[0].counts == (1,) * 8


def test_extra_fields_with_plain_values_are_allowed():
    log = '{"playDatas": ["' + entry("Song A", [1] * 8) + '"], "version": 3, "debug": false, "note": null}'
    assert len(parse_count_log(log)) == 1


def test_a_title_may_contain_an_apostrophe_or_a_star():
    log = repr({"playDatas": [entry("Don't*Stop", [2] * 8)]})
    assert parse_count_log(log)[0].title == "Don't*Stop"


def test_known_alias_is_mapped():
    log = repr({"playDatas": [entry("오르트 구름", [0] * 8)]})
    assert parse_count_log(log)[0].title == "Oort Cloud"


def test_entries_for_the_same_song_are_added_up():
    log = repr(
        {
            "playDatas": [
                entry("Oort Cloud", [1] * 8),
                entry("Song A", [5] * 8),
                entry("오르트 구름", range(8)),
            ]
        }
    )
    assert parse_count_log(log) == [
        SongCounts("Oort Cloud", tuple(1 + j for j in range(8))),
        SongCounts("Song A", (5,) * 8),
    ]


def test_counts_that_add_up_past_mysql_int_are_rejected():
    log = repr({"playDatas": [entry("Song A", [MAX_COUNT] * 8), entry("Song A", [1] * 8)]})
    with pytest.raises(CountLogError, match="add up"):
        parse_count_log(log)


def test_the_largest_count_mysql_int_holds_is_accepted():
    log = repr({"playDatas": [entry("Song A", [MAX_COUNT] * 8)]})
    assert parse_count_log(log)[0].counts == (MAX_COUNT,) * 8


def test_a_title_is_stripped():
    log = repr({"playDatas": [entry("  Song A ", [0] * 8)]})
    assert parse_count_log(log)[0].title == "Song A"


@pytest.mark.parametrize(
    "log",
    [
        '{"playDatas": ["Song \\ud800*' + "*".join(["1"] * 8) + '"]}',  # JSON escape
        "{'playDatas': ['Song \\udfff*" + "*".join(["1"] * 8) + "']}",  # Python escape
    ],
)
def test_a_title_with_half_a_surrogate_pair_is_rejected(log):
    with pytest.raises(CountLogError, match="not valid Unicode"):
        parse_count_log(log)


@pytest.mark.parametrize(
    "log",
    [
        "not a log",
        "",
        "{'nothing': []}",
        repr({"playDatas": ["Song A*1*2"]}),
        repr({"playDatas": [entry("Song A", ["x"] * 8)]}),
        repr({"playDatas": [entry("Song A", [-1] * 8)]}),
        repr({"playDatas": [1]}),
        repr({"playDatas": [entry("", [1] * 8)]}),
        repr({"playDatas": [entry("   ", [1] * 8)]}),
        repr({"playDatas": [entry("\t", [1] * 8)]}),
    ],
)
def test_rejects_malformed_logs(log):
    with pytest.raises(CountLogError):
        parse_count_log(log)


@pytest.mark.parametrize(
    "count",
    [
        "+2",  # int() takes these four
        "1_000",
        " 3",
        "٣",  # ARABIC-INDIC DIGIT THREE
        "",
        "1.0",
        str(MAX_COUNT + 1),  # no longer fits a MySQL INT
        "99999999999",
        "9" * 5000,  # past Python's int() digit limit
    ],
)
def test_a_count_must_be_ascii_digits_within_mysql_int(count):
    log = repr({"playDatas": ["Song A*" + "*".join(["0"] * 7 + [count])]})
    with pytest.raises(CountLogError):
        parse_count_log(log)


# inputs that used to escape as RecursionError, MemoryError, TypeError or a bare ValueError (a 500)
HOSTILE_LOGS = {
    "deep brackets": "[" * 150_000,
    "deep braces": "{" * 150_000,
    "deep parentheses": "(" * 150_000,
    "unary minus chain": "-" * 150_000 + "1",
    "subscript chain": "None" + "[0]" * 100_000,
    "string subscript chain": "'a'" + "[0]" * 100_000,
    "f-string": "f'{" + "[" * 1000 + "]" * 1000 + "}'",
    "unhashable key": "{[]: 1}",
    "set of dicts": "{{}}",
    "huge JSON number": '{"playDatas": [], "n": ' + "1" * 5000 + "}",
    "nested past the limit": "{'playDatas': [[[[['x']]]]]}",
    "bytes": "{'playDatas': [b'x']}",
    "name": "{'playDatas': [__import__]}",
    "call": "{'playDatas': [print()]}",
    "null byte": "{'playDatas': ['\x00']}",
    "unterminated string": "{'playDatas': ['x]}",
    "unbalanced": "{'playDatas': ['x']]}",
}


@pytest.mark.parametrize("log", HOSTILE_LOGS.values(), ids=HOSTILE_LOGS.keys())
def test_hostile_logs_are_a_parse_error_not_a_crash(log):
    with pytest.raises(CountLogError):
        parse_count_log(log)


# ---------- API, on SQLite in memory (or on MySQL when TEST_DATABASE_URL is set) ----------

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "schema.sql"


def make_engine(url=TEST_DATABASE_URL):
    if not url:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        db_session.metadata.create_all(engine)
        return engine
    # the tests drop and recreate tables that have the production names, so only a test database will do
    database = make_url(url).database or ""
    if not database.endswith("test"):
        raise RuntimeError(f"TEST_DATABASE_URL must name a database ending in 'test', not {database!r}")
    engine = db_session.create_db_engine(url)  # the pool the app runs with
    lines = SCHEMA_SQL.read_text().splitlines()
    ddl = "\n".join(line for line in lines if not line.lstrip().startswith("--"))
    with engine.begin() as conn:
        for table in reversed(db_session.metadata.sorted_tables):
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table.name}")
        for statement in ddl.split(";"):
            if statement.strip():
                conn.exec_driver_sql(statement)
    return engine


@pytest.fixture
def client(monkeypatch):
    engine = make_engine()
    with engine.begin() as conn:
        # two songs with eight charts each; "Song B" starts at 9
        conn.execute(
            insert(db_session.music_tb),
            [
                {"music_key": k, "name": name}
                for name, start in (("Song A", 1), ("Song B", 9))
                for k in range(start, start + CHARTS_PER_SONG)
            ],
        )
    monkeypatch.setattr(db_session, "get_engine", lambda: engine)
    monkeypatch.setattr("app.main.get_engine", lambda: engine)
    with TestClient(app) as c:
        c.engine = engine
        yield c
    engine.dispose()


def post(client, device_id, songs, **extra):
    log = repr({"playDatas": [entry(t, c) for t, c in songs]})
    return client.post("/insert_playcount", json={"device_id": device_id, "count_log": log, **extra})


def rows(client, table):
    with client.engine.connect() as conn:
        return conn.execute(select(table).order_by(*table.primary_key)).all()


def test_stores_one_row_per_chart(client):
    r = post(client, "dev-1", [("Song A", range(8)), ("Song B", [5] * 8)])
    assert r.status_code == 200
    body = r.json()
    assert (body["saved"], body["unknown_titles"], body["duplicate"]) == (16, [], False)
    stored = {(row.music_key, row.count) for row in rows(client, db_session.playcount_tb)}
    assert stored == {(1 + j, j) for j in range(8)} | {(9 + j, 5) for j in range(8)}


def test_the_request_the_client_sends_today_still_works(client):
    # no report_id: the server makes one up, so the report is stored and can be told apart
    r = post(client, "dev-1", [("Song A", [1] * 8)])
    assert r.status_code == 200
    [report] = rows(client, db_session.report_tb)
    assert report.report_id == r.json()["report_id"]
    assert report.reported_at is not None
    assert {row.report_id for row in rows(client, db_session.playcount_tb)} == {report.report_id}


def test_reports_are_kept_apart_and_in_order(client):
    first = post(client, "dev-1", [("Song A", [1] * 8)]).json()["report_id"]
    second = post(client, "dev-1", [("Song A", [2] * 8)]).json()["report_id"]
    assert first != second
    reports = sorted(rows(client, db_session.report_tb), key=lambda r: r.reported_at)
    assert [r.report_id for r in reports] == [first, second]
    by_report = {}
    for row in rows(client, db_session.playcount_tb):
        by_report.setdefault(row.report_id, set()).add(row.count)
    assert by_report == {first: {1}, second: {2}}


def test_a_retried_report_is_stored_once(client):
    first = post(client, "dev-1", [("Song A", [1] * 8)], report_id="r-1")
    retry = post(client, "dev-1", [("Song A", [1] * 8)], report_id="r-1")
    assert first.json() == {"saved": 8, "unknown_titles": [], "report_id": "r-1", "duplicate": False}
    assert retry.json() == {"saved": 8, "unknown_titles": [], "report_id": "r-1", "duplicate": True}
    assert len(rows(client, db_session.report_tb)) == 1
    assert len(rows(client, db_session.playcount_tb)) == 8


def test_a_reused_report_id_with_other_counts_is_refused(client):
    post(client, "dev-1", [("Song A", [1] * 8)], report_id="r-1")
    reused = post(client, "dev-1", [("Song A", [2] * 8)], report_id="r-1")
    assert reused.status_code == 409
    assert {row.count for row in rows(client, db_session.playcount_tb)} == {1}


def test_a_retry_in_another_quoting_style_is_still_a_retry(client):
    counts = [("Song A", [1] * 8)]
    post(client, "dev-1", counts, report_id="r-1")
    log = '{"playDatas": ["' + entry("Song A", [1] * 8) + '"], "version": 2}'  # JSON, with an extra field
    body = {"device_id": "dev-1", "count_log": log, "report_id": "r-1"}
    retry = client.post("/insert_playcount", json=body)
    assert retry.status_code == 200 and retry.json()["duplicate"] is True


def test_a_song_named_twice_is_stored_once_with_its_counts_added(client):
    r = post(
        client, "dev-1", [("Song A", [1] * 8), ("Song A", [2] * 8), ("Nope", [1] * 8), ("Nope", [1] * 8)]
    )
    assert (r.json()["saved"], r.json()["unknown_titles"]) == (8, ["Nope"])
    stored = sorted((row.music_key, row.count) for row in rows(client, db_session.playcount_tb))
    assert stored == [(1 + j, 3) for j in range(8)]


def test_unknown_titles_are_logged_as_a_count_and_a_short_escaped_sample(client, caplog):
    titles = [f"Unknown {i}\nFORGED " + "x" * 100 for i in range(20)]
    post(client, "dev-1", [(t, [1] * 8) for t in titles])
    [record] = [r for r in caplog.records if r.name == "wjmax"]
    message = record.getMessage()
    assert message.startswith("20 unknown titles from dev-1: ")
    assert "\n" not in message and "Unknown 4" in message and "Unknown 5" not in message
    assert len(message) < 400


def test_a_report_id_belongs_to_one_device(client):
    post(client, "dev-1", [("Song A", [1] * 8)], report_id="r-1")
    other = post(client, "dev-2", [("Song A", [1] * 8)], report_id="r-1")
    assert other.json()["duplicate"] is False
    assert len(rows(client, db_session.playcount_tb)) == 16


@pytest.mark.parametrize("report_id", ["", "x" * 65, "has space", "semi;colon"])
def test_a_bad_report_id_is_rejected(client, report_id):
    assert post(client, "dev-1", [("Song A", [1] * 8)], report_id=report_id).status_code == 422


def test_a_device_is_registered_once(client):
    post(client, "dev-1", [("Song A", [1] * 8)])
    first_seen = rows(client, db_session.user_tb)[0].insert_date
    post(client, "dev-1", [("Song A", [2] * 8)])
    users = rows(client, db_session.user_tb)
    assert len(users) == 1 and users[0].insert_date == first_seen
    assert len(rows(client, db_session.playcount_tb)) == 16


def test_unknown_titles_are_reported_not_stored(client):
    r = post(client, "dev-1", [("Song A", [1] * 8), ("No Such Song", [1] * 8)])
    assert (r.json()["saved"], r.json()["unknown_titles"]) == (8, ["No Such Song"])


def test_a_malformed_log_is_rejected_and_nothing_is_stored(client):
    r = client.post("/insert_playcount", json={"device_id": "dev-1", "count_log": "garbage"})
    assert r.status_code == 422
    assert rows(client, db_session.user_tb) == []


@pytest.mark.parametrize("name", ["deep brackets", "unary minus chain", "subscript chain", "unhashable key"])
def test_a_hostile_log_is_a_422(client, name):
    r = client.post("/insert_playcount", json={"device_id": "dev-1", "count_log": HOSTILE_LOGS[name]})
    assert r.status_code == 422
    assert rows(client, db_session.user_tb) == []


def test_a_count_too_big_for_mysql_is_a_422(client):
    r = post(client, "dev-1", [("Song A", [99999999999] * 8)])
    assert r.status_code == 422
    assert rows(client, db_session.playcount_tb) == []


def test_device_id_is_required(client):
    r = client.post("/insert_playcount", json={"device_id": "", "count_log": "{}"})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "device_id",
    ["dev 1", "dev-1 ", "dev\n2026-10-20 INFO forged line", "dev\x00", "dev\t1", "dev\u2028", "dev\u200b"],
)
def test_a_device_id_with_spaces_or_control_characters_is_rejected(client, device_id):
    assert post(client, device_id, [("Song A", [1] * 8)]).status_code == 422
    assert rows(client, db_session.user_tb) == []


@pytest.mark.parametrize(
    "device_id",
    ["3f2a9c0e1b7d4e8fa6b5c4d3e2f1a0b9c8d7e6f5", "550e8400-e29b-41d4-a716-446655440000", "기기-1"],
)
def test_ordinary_device_ids_are_accepted(client, device_id):
    assert post(client, device_id, [("Song A", [1] * 8)]).status_code == 200


LOG_A = repr({"playDatas": [entry("Song A", [1] * 8)]})
LONE_SURROGATE_BODIES = {
    "in device_id": {"device_id": "dev\ud800", "count_log": LOG_A},
    "in count_log": {"device_id": "dev-1", "count_log": "{'playDatas': ['\ud800']}"},
    # the log is valid text, but the title in it decodes to a lone surrogate
    "escaped inside count_log": {
        "device_id": "dev-1",
        "count_log": "{'playDatas': ['" + entry("A\\ud800", [1] * 8) + "']}",
    },
}


@pytest.mark.parametrize("body", LONE_SURROGATE_BODIES.values(), ids=LONE_SURROGATE_BODIES.keys())
def test_a_lone_surrogate_is_a_422(client, body):
    # json.dumps writes a lone surrogate as the escape \ud800; httpx's json= cannot encode one at all
    raw = json.dumps(body).encode()
    r = client.post("/insert_playcount", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert rows(client, db_session.user_tb) == []


def test_a_422_does_not_echo_the_input(client):
    r = client.post("/insert_playcount", json={"device_id": "", "count_log": "x" * 100_000})
    assert r.status_code == 422
    assert [set(error) for error in r.json()["detail"]] == [{"loc", "msg", "type"}]
    assert len(r.content) < 1000


@pytest.mark.parametrize(
    "body",
    [
        {"device_id": "dev-1", "count_log": "garbage"},
        {"device_id": "", "count_log": LOG_A},
        {"device_id": "dev-1", "count_log": LOG_A, "report_id": "not valid"},
    ],
)
def test_malformed_input_is_a_422_even_when_the_database_is_down(client, monkeypatch, body):
    down = create_engine("sqlite:////nonexistent-dir/wjmax.db")
    monkeypatch.setattr("app.main.get_engine", lambda: down)
    assert client.post("/insert_playcount", json=body).status_code == 422
    failing = TestClient(app, raise_server_exceptions=False)
    assert post(failing, "dev-1", [("Song A", [1] * 8)]).status_code == 500  # the database really is down


def test_requests_run_in_as_many_threads_as_the_pool_has_connections(client):
    threads = client.portal.call(lambda: to_thread.current_default_thread_limiter().total_tokens)
    assert threads == REQUEST_THREADS
    engine = db_session.create_db_engine("mysql+pymysql://user:pw@127.0.0.1:3306/wjmax_test")
    assert engine.pool.size() + engine.pool._max_overflow == REQUEST_THREADS


def test_an_oversized_body_is_refused_from_its_content_length(client):
    body = b"x" * (MAX_BODY_BYTES + 1)
    r = client.post("/insert_playcount", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_an_oversized_chunked_body_is_refused(client):
    chunks = (b"x" * 65536 for _ in range(50))  # no Content-Length, about 3 MB in all
    r = client.post("/insert_playcount", content=chunks, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert rows(client, db_session.user_tb) == []


def test_a_chunked_body_stops_being_read_at_the_limit():
    # driven over raw ASGI, because TestClient buffers a streamed body before the app sees it
    chunk, pulled, sent = b"x" * 65536, 0, []

    async def receive():
        nonlocal pulled
        pulled += 1
        return {"type": "http.request", "body": chunk, "more_body": pulled < 1000}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/insert_playcount",
        "raw_path": b"/insert_playcount",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    anyio.run(app, scope, receive, send)
    assert sent[0]["status"] == 413
    assert pulled == MAX_BODY_BYTES // len(chunk) + 1


def test_health_check(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_root_and_docs_are_not_exposed(client):
    assert client.get("/").status_code == 404
    assert client.get("/docs").status_code == 404


def test_a_failed_write_stores_nothing(client):
    # the play counts cannot be written, so the device and the report are rolled back with them
    with client.engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE playcount_tb")
    failing = TestClient(app, raise_server_exceptions=False)
    r = post(failing, "dev-1", [("Song A", [1] * 8)])
    assert r.status_code == 500
    assert rows(client, db_session.user_tb) == []
    assert rows(client, db_session.report_tb) == []


@pytest.mark.parametrize("database", ["wjmax_db", "production", None])
def test_the_tests_refuse_a_database_not_named_for_tests(database):
    url = "mysql+pymysql://user:pw@127.0.0.1:3306" + (f"/{database}" if database else "")
    with pytest.raises(RuntimeError, match="ending in 'test'"):
        make_engine(url)


# titles that MySQL's default collation (utf8mb4_0900_ai_ci) would fold together
LOOKALIKE_TITLES = ["Glory", "GLORY", "Cafe", "Café", "ゆめ", "ユメ"]


def test_titles_that_differ_only_in_case_accent_or_kana_are_different_songs(client):
    starts = {title: 101 + 8 * i for i, title in enumerate(LOOKALIKE_TITLES)}
    with client.engine.begin() as conn:
        conn.execute(
            insert(db_session.music_tb),
            [
                {"music_key": start + j, "name": t}
                for t, start in starts.items()
                for j in range(CHARTS_PER_SONG)
            ],
        )
    r = post(client, "dev-1", [(t, [i + 1] * 8) for i, t in enumerate(LOOKALIKE_TITLES)])
    assert r.json()["unknown_titles"] == [] and r.json()["saved"] == 8 * len(LOOKALIKE_TITLES)
    stored = {(row.music_key, row.count) for row in rows(client, db_session.playcount_tb)}
    expected = {
        (starts[t] + j, i + 1) for i, t in enumerate(LOOKALIKE_TITLES) for j in range(CHARTS_PER_SONG)
    }
    assert stored == expected


@pytest.mark.parametrize("device_id, report_id", [("DEV-1", "r-1"), ("dev-1", "R-1")])
def test_ids_that_differ_only_in_case_are_not_retries(client, device_id, report_id):
    post(client, "dev-1", [("Song A", [1] * 8)], report_id="r-1")
    other = post(client, device_id, [("Song A", [1] * 8)], report_id=report_id)
    assert other.json()["duplicate"] is False
    assert len(rows(client, db_session.playcount_tb)) == 16


# ---------- MySQL only (the CI job with a MySQL 8 service) ----------


@needs_mysql
def test_text_keys_compare_exactly_in_schema_sql(client):
    query = text(
        "SELECT CONCAT(table_name, '.', column_name), collation_name FROM information_schema.columns"
        " WHERE table_schema = DATABASE() AND data_type = 'varchar'"
    )
    with client.engine.connect() as conn:
        found = dict(conn.execute(query).all())
    expected = ["user_tb.device_id", "music_tb.name", "report_tb.device_id", "report_tb.report_id"]
    expected += ["playcount_tb.device_id", "playcount_tb.report_id"]
    assert found == dict.fromkeys(expected, "utf8mb4_0900_bin")


def mysql_type(type_, dialect):
    # a reflected VARCHAR with its own collation also names its character set; every table is utf8mb4
    return type_.compile(dialect).replace(" CHARACTER SET utf8mb4", "")


@needs_mysql
def test_schema_sql_declares_the_tables_the_code_uses(client):
    # MySQL runs schema.sql; the code (and SQLite in these tests) uses the tables in db_session.py
    found, dialect = inspect(client.engine), client.engine.dialect
    for table in db_session.metadata.sorted_tables:
        columns = {c["name"]: c for c in found.get_columns(table.name)}
        assert list(columns) == list(table.c.keys()), table.name
        for column in table.c:
            reflected, where = columns[column.name], f"{table.name}.{column.name}"
            assert mysql_type(reflected["type"], dialect) == mysql_type(column.type, dialect), where
            assert reflected["nullable"] == column.nullable, where
            assert (reflected.get("autoincrement") is True) == (column is table.autoincrement_column), where

        primary_key = found.get_pk_constraint(table.name)["constrained_columns"]
        assert primary_key == list(table.primary_key.columns.keys()), table.name
        foreign_keys = {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in found.get_foreign_keys(table.name)
        }
        assert foreign_keys == {
            (tuple(fk.column_keys), fk.referred_table.name, tuple(e.column.name for e in fk.elements))
            for fk in table.foreign_key_constraints
        }, table.name
        indexes = {
            (i["name"], tuple(i["column_names"]), bool(i["unique"])) for i in found.get_indexes(table.name)
        }
        assert indexes == {(i.name, tuple(c.name for c in i.columns), bool(i.unique)) for i in table.indexes}
        charset = found.get_table_options(table.name)["mysql_default charset"]
        assert charset == table.kwargs["mysql_charset"], table.name


@needs_mysql
def test_concurrent_deliveries_of_one_report_store_it_once(client):
    post(client, "dev-1", [("Song A", [1] * 8)])  # the device already exists
    songs = [SongCounts("Song A", (2,) * 8)]
    second = {}

    def deliver_again():
        with client.engine.begin() as conn:
            second["result"] = save_play_counts(conn, "dev-1", "r-1", songs)

    with client.engine.connect() as conn:
        conn.begin()
        save_play_counts(conn, "dev-1", "r-1", songs)
        thread = threading.Thread(target=deliver_again)
        thread.start()
        thread.join(timeout=2)
        assert thread.is_alive(), "the second delivery should wait for the first one's commit"
        conn.commit()
    thread.join(timeout=30)
    assert second["result"].duplicate is True
    assert second["result"].saved == 8
    assert len([r for r in rows(client, db_session.playcount_tb) if r.report_id == "r-1"]) == 8


@needs_mysql
def test_more_clients_than_threads_and_connections_are_all_answered(client):
    # 60 clients at once, more than the 40 worker threads. With the connection taken by a FastAPI
    # dependency, every thread ended up waiting for one and 281 of 600 requests timed out with a 500.
    clients, reports_each = 60, 5
    statuses = []

    def send_reports(i):
        for j in range(reports_each):
            try:
                status = post(client, f"dev-{i}", [("Song A", [j] * 8)], report_id=f"r-{j}").status_code
            except Exception as e:  # a pool timeout surfaces here as the server's exception
                status = type(e).__name__
            statuses.append(status)

    threads = [threading.Thread(target=send_reports, args=(i,)) for i in range(clients)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.monotonic() - started
    assert Counter(statuses) == {200: clients * reports_each}
    assert len(rows(client, db_session.report_tb)) == clients * reports_each
    assert elapsed < 25, f"{elapsed:.0f} s: requests waited for connections"
