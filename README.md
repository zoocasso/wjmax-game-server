# WJMAX game server

[![tests](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml/badge.svg)](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml)

[English](#english) · [한국어](#한국어)

## English

The play-log ingestion API of **WJMAX**, a fan-made rhythm game in the Woowakgood community. Side project, Aug 2023 – Feb 2024, two people: the main developer built the game and I was the sole server developer (server, security layer, database). About 300 players were online on average and about 2,000 at the peak of an update day.

In production: **game client → Cloudflare (proxy, WAF) → AWS EC2 (FastAPI in Docker) → AWS RDS (MySQL)**.

This repository holds the service's API, cleaned up and rewritten in October 2026. The request the game client sends is unchanged.

### Design

- **One transaction per request.** A report is stored completely or not at all; malformed input is rejected with `422` before anything is written.
- **Devices are registered once.** The first report creates the device (`INSERT IGNORE`) and later reports keep its first-seen time.
- **One lookup per report.** The first chart key of every song in a report comes from a single grouped query.
- **Every report is a row.** `report_tb` records each report under `(device_id, report_id)` with the time the server received it (`reported_at`), and every play-count row points to its report, so a device's snapshots can be told apart and ordered.
- **A retried report is stored once.** A client may send its own `report_id`; a second delivery with the same id is answered with `"duplicate": true` and writes nothing, even when both arrive at once (the key makes the second `INSERT IGNORE` wait for the first). The game client as it was released sends no id, so the server assigns one and its retries are stored as separate reports.
- **Validated input.** `count_log` is tokenized before it is parsed and may hold only objects, lists, strings, numbers and keywords, at most four levels deep, so hostile input is a `422` instead of a crash inside the JSON or Python parser. Each entry is a non-blank title and eight counts written in ASCII digits that fit a MySQL `INT`. Bodies over 1 MB are refused with `413` before they are read. Songs that are not in `music_tb` are skipped and returned in `unknown_titles`.
- **Starts without the database.** Tables are declared in code ([`schema.sql`](schema.sql) has the DDL), the engine is created on first use, and stale connections are checked before use. `GET /healthz` reports database trouble as `503`.
- **No secrets in the image.** Settings come from the environment at run time, the container runs as a non-root user, and the API docs are off unless `ENABLE_DOCS=1`.
- **Tested.** [`tests/`](tests/) covers parsing and the API. GitHub Actions runs them on SQLite and again on MySQL 8.4 with the tables from `schema.sql`, which also checks that `schema.sql` matches the code and that concurrent retries are stored once.

### API

`POST /insert_playcount`, as the game client sends it:

```json
{"device_id": "…", "count_log": "{'playDatas': ['Oort Cloud*3*1*0*0*2*0*0*0']}"}
```

Each entry is a song title and the play count of each of its eight charts. An optional `"report_id"` (1–64 letters, digits, `-` or `_`) makes retries safe. The response:

```json
{"saved": 8, "unknown_titles": [], "report_id": "…", "duplicate": false}
```

### Run

```bash
cp .env.example .env              # set DATABASE_URL
mysql wjmax_db < schema.sql
pip install -r requirements.txt
uvicorn app.main:app --reload
python client.py                  # sends one report
```

With Docker: `docker build -t wjmax-server .` and `docker run --env-file .env -p 8000:8000 wjmax-server`.

Tests: `pip install -r requirements-dev.txt` and `python -m pytest -q`. Set `TEST_DATABASE_URL` to an empty MySQL database to run them on MySQL as well; the tests drop and recreate the tables there.

## 한국어

우왁굳 팬게임 **왁제이맥스(WJMAX)**의 플레이 로그 수집 API입니다. 사이드 프로젝트(2023.08 ~ 2024.02, 2인 팀)로, 게임은 메인 개발자가 만들고 저는 서버를 단독으로 맡아 서버·보안 계층·데이터베이스를 담당했습니다. 동시 접속은 평균 약 300명, 업데이트 날 최대 약 2,000명이었습니다.

운영 구성: **게임 클라이언트 → Cloudflare(프록시, WAF) → AWS EC2(Docker의 FastAPI) → AWS RDS(MySQL)**.

이 저장소는 서비스 API를 2026년 10월에 정리해 다시 쓴 것입니다. 게임 클라이언트가 보내는 요청은 그대로입니다.

- **요청 하나에 트랜잭션 하나**: 보고 하나는 전부 저장되거나 전혀 저장되지 않습니다. 잘못된 입력은 아무것도 쓰기 전에 `422`로 거절합니다.
- **기기는 한 번만 등록**: 첫 보고에서 기기를 만들고(`INSERT IGNORE`), 이후 보고는 처음 본 시각을 유지합니다.
- **조회는 보고당 한 번**: 보고에 담긴 모든 곡의 첫 차트 키를 그룹 쿼리 하나로 가져옵니다.
- **보고마다 한 행**: `report_tb`에 보고를 `(device_id, report_id)`와 서버가 받은 시각(`reported_at`)으로 남기고, 플레이 횟수 행은 모두 자기 보고를 가리킵니다. 그래서 한 기기의 스냅숏을 서로 구분하고 순서대로 볼 수 있습니다.
- **재전송은 한 번만 저장**: 클라이언트가 `report_id`를 보내면, 같은 id로 다시 온 보고는 아무것도 쓰지 않고 `"duplicate": true`로 답합니다. 두 번이 동시에 와도 키 때문에 두 번째 `INSERT IGNORE`가 첫 번째를 기다립니다. 배포된 게임 클라이언트는 id를 보내지 않으므로 서버가 id를 붙이고, 그 재전송은 별개의 보고로 저장됩니다.
- **입력 검증**: `count_log`는 파싱 전에 토큰 단위로 검사해 객체·리스트·문자열·숫자·키워드만, 최대 4단계 중첩까지 받습니다. 그래서 악의적인 입력도 JSON·Python 파서 안에서 죽지 않고 `422`가 됩니다. 각 항목은 공백이 아닌 곡 제목과 ASCII 숫자로 쓴, MySQL `INT`에 들어가는 횟수 8개여야 합니다. 1MB가 넘는 요청 본문은 다 읽기 전에 `413`으로 거절합니다. `music_tb`에 없는 곡은 건너뛰고 `unknown_titles`로 돌려줍니다.
- **DB 없이도 시작**: 테이블은 코드와 [`schema.sql`](schema.sql)에 선언하고, 엔진은 처음 쓸 때 만들며, 오래된 연결은 쓰기 전에 확인합니다. `GET /healthz`는 DB 문제를 `503`으로 알립니다.
- **이미지에 비밀값 없음**: 설정은 실행할 때 환경 변수로 받고, 컨테이너는 root가 아닌 사용자로 돌며, API 문서는 `ENABLE_DOCS=1`일 때만 엽니다.
- **테스트**: [`tests/`](tests/)의 파싱·API 테스트를 GitHub Actions가 push마다 SQLite와, `schema.sql`로 만든 MySQL 8.4에서 각각 돌립니다. MySQL 쪽은 `schema.sql`이 코드와 맞는지, 동시에 온 재전송이 한 번만 저장되는지도 확인합니다.

실행 방법은 위의 [Run](#run)과 같습니다.
