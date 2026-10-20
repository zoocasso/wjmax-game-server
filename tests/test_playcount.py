import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, insert, select  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db_session  # noqa: E402
from app.main import app  # noqa: E402
from app.playcount import CHARTS_PER_SONG, CountLogError, parse_count_log  # noqa: E402


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


def test_a_title_may_contain_an_apostrophe_or_a_star():
    log = repr({"playDatas": [entry("Don't*Stop", [2] * 8)]})
    assert parse_count_log(log)[0].title == "Don't*Stop"


def test_known_alias_is_mapped():
    log = repr({"playDatas": [entry("오르트 구름", [0] * 8)]})
    assert parse_count_log(log)[0].title == "Oort Cloud"


@pytest.mark.parametrize(
    "log",
    [
        "not a log",
        "{'nothing': []}",
        repr({"playDatas": ["Song A*1*2"]}),
        repr({"playDatas": [entry("Song A", ["x"] * 8)]}),
        repr({"playDatas": [entry("Song A", [-1] * 8)]}),
        repr({"playDatas": [1]}),
    ],
)
def test_rejects_malformed_logs(log):
    with pytest.raises(CountLogError):
        parse_count_log(log)


# ---------- API, on an in-memory database ----------


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db_session.metadata.create_all(engine)
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


def post(client, device_id, songs):
    log = repr({"playDatas": [entry(t, c) for t, c in songs]})
    return client.post("/insert_playcount", json={"device_id": device_id, "count_log": log})


def rows(client, table):
    with client.engine.connect() as conn:
        return conn.execute(select(table)).all()


def test_stores_one_row_per_chart(client):
    r = post(client, "dev-1", [("Song A", range(8)), ("Song B", [5] * 8)])
    assert r.status_code == 200
    assert r.json() == {"saved": 16, "unknown_titles": []}
    stored = {(m, c) for _, m, c in rows(client, db_session.playcount_tb)}
    assert stored == {(1 + j, j) for j in range(8)} | {(9 + j, 5) for j in range(8)}


def test_a_device_is_registered_once(client):
    post(client, "dev-1", [("Song A", [1] * 8)])
    first_seen = rows(client, db_session.user_tb)[0].insert_date
    post(client, "dev-1", [("Song A", [2] * 8)])
    users = rows(client, db_session.user_tb)
    assert len(users) == 1 and users[0].insert_date == first_seen
    assert len(rows(client, db_session.playcount_tb)) == 16


def test_unknown_titles_are_reported_not_stored(client):
    r = post(client, "dev-1", [("Song A", [1] * 8), ("No Such Song", [1] * 8)])
    assert r.json() == {"saved": 8, "unknown_titles": ["No Such Song"]}


def test_a_malformed_log_is_rejected_and_nothing_is_stored(client):
    r = client.post("/insert_playcount", json={"device_id": "dev-1", "count_log": "garbage"})
    assert r.status_code == 422
    assert rows(client, db_session.user_tb) == []


def test_device_id_is_required(client):
    r = client.post("/insert_playcount", json={"device_id": "", "count_log": "{}"})
    assert r.status_code == 422


def test_health_check(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_root_and_docs_are_not_exposed(client):
    assert client.get("/").status_code == 404
    assert client.get("/docs").status_code == 404


def test_a_failed_write_stores_nothing(client):
    # the play counts cannot be written, so the device registered in the same transaction is rolled back
    with client.engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE playcount_tb")
    failing = TestClient(app, raise_server_exceptions=False)
    r = post(failing, "dev-1", [("Song A", [1] * 8)])
    assert r.status_code == 500
    assert rows(client, db_session.user_tb) == []
