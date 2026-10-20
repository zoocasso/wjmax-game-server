# WJMAX game server

[![tests](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml/badge.svg)](https://github.com/zoocasso/wjmax-game-server/actions/workflows/ci.yml)

[English](#english) · [한국어](#한국어)

## English

The play-log ingestion API of **WJMAX**, a fan-made rhythm game in the Woowakgood community. Side project, Aug 2023 – Feb 2024, two people: the main developer built the game and I was the sole server developer (server, security layer, database). About 300 players were online on average and about 2,000 at the peak of an update day.

In production: **game client → Cloudflare (proxy, WAF) → AWS EC2 (FastAPI in Docker) → AWS RDS (MySQL)**.

This repository holds the service's API, cleaned up and rewritten in October 2026. The request the game client sends is unchanged.

### Design

- **One transaction per request.** A report is stored completely or not at all. Input is checked before the request takes a database connection, so malformed input is a `422` even when the database is down.
- **Devices are registered once.** The first report creates the device (`INSERT IGNORE`) and later reports keep its first-seen time.
- **One lookup per report.** The first chart key of every song in a report comes from a single grouped query.
- **A connection for every worker thread.** FastAPI runs each request in one of 40 worker threads. The request takes its connection in that thread, after its input has been checked, and the pool can open 40 connections, so no request waits for one. An earlier version of this rewrite took the connection in a FastAPI dependency, which starved the pool: in a local load test with 60 clients sending at once, 281 of 600 requests failed with a pool timeout.
- **Every report is a row.** `report_tb` records each report under `(device_id, report_id)` with the time the server received it (`reported_at`), and every play-count row points to its report, so a device's snapshots can be told apart and ordered.
- **A retried report is stored once.** A client may send its own `report_id`; a second delivery with the same id is answered with `"duplicate": true` and writes nothing, even when both arrive at once (the key makes the second `INSERT IGNORE` wait for the first). The game client as it was released sends no id, so the server assigns one and its retries are stored as separate reports. A `report_id` the device already used, sent with different play counts, is refused with `409`: `report_tb` keeps a SHA-256 of each report's parsed play counts, so a retry still matches when it is quoted differently.
- **Entries are stored as sent.** A song named twice in one report is stored twice under that report ([`client.py`](client.py) sends "Oort Cloud" and its alias "오르트 구름", which map to the same song). The server does not guess whether to add the counts, keep one or drop one; that is left to whoever reads the data.
- **Validated input.** `count_log` is tokenized before it is parsed and may hold only objects, lists, strings, numbers and keywords, at most four levels deep, so hostile input is a `422` instead of a crash inside the JSON or Python parser. Each entry is a non-blank title and eight counts written in ASCII digits that fit a MySQL `INT`. Bodies over 1 MB are refused with `413`: at once when `Content-Length` says so, and otherwise as soon as a chunked body passes 1 MB. Songs that are not in `music_tb` are skipped and returned in `unknown_titles`. `device_id` may not contain spaces, line breaks or other control characters, because it is written to the log. Text that is not valid Unicode (a lone surrogate) is a `422`, and a `422` names the field and the problem without echoing the input back.
- **Exact matching.** Titles and ids compare byte for byte (`utf8mb4_0900_bin`). MySQL's default collation ignores case, accents and kana, which would merge songs such as "Glory" and "GLORY" or "ゆめ" and "ユメ" and treat report `R-1` as a retry of `r-1`.
- **No authentication.** The released game client sends no credentials, so anyone who knows the URL can post a report under any `device_id`. Input validation, the body limit and Cloudflare in front of the server are what bound abuse; reports are not proof of who played.
- **Starts without the database.** Tables are declared in code ([`schema.sql`](schema.sql) has the DDL), the engine is created on first use, and stale connections are checked before use. `GET /healthz` reports database trouble as `503`.
- **No secrets in the image.** Settings come from the environment at run time, the container runs as a non-root user, and the API docs are off unless `ENABLE_DOCS=1`.
- **Tested.** [`tests/`](tests/) covers parsing and the API. GitHub Actions runs them on SQLite and again on MySQL 8.0 and 8.4 with the tables from `schema.sql`, which also checks that `schema.sql` matches the code, that titles and ids compare exactly, that concurrent retries are stored once and that 60 clients sending at once are all answered. The MySQL jobs fail if any test is skipped.

### API

`POST /insert_playcount`, as the game client sends it:

```json
{"device_id": "…", "count_log": "{'playDatas': ['Oort Cloud*3*1*0*0*2*0*0*0']}"}
```

Each entry is a song title and the play count of each of its eight charts. An optional `"report_id"` (1–64 letters, digits, `-` or `_`) makes retries safe. The response:

```json
{"saved": 8, "unknown_titles": [], "report_id": "…", "duplicate": false}
```

Errors: `422` for malformed input, `409` for a `report_id` reused with other play counts, `413` for a body over 1 MB.

### Run

A local MySQL in Docker, with the tables from `schema.sql` and one sample song from `seed.sql`:

```bash
docker run -d --name wjmax-mysql -e MYSQL_ROOT_PASSWORD=change-me -e MYSQL_DATABASE=wjmax_db -p 3306:3306 mysql:8.4
until docker exec wjmax-mysql mysqladmin ping -h 127.0.0.1 -uroot -pchange-me --silent; do sleep 2; done
docker exec -i wjmax-mysql mysql -uroot -pchange-me wjmax_db < schema.sql
docker exec -i wjmax-mysql mysql -uroot -pchange-me wjmax_db < seed.sql
cp .env.example .env              # its DATABASE_URL points at this container
```

The server, and in a second terminal the sample client:

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
set -a && . ./.env && set +a      # export the settings in .env; uvicorn does not read the file
uvicorn app.main:app --reload
python3 client.py                 # in the second terminal: sends one report, answers 200 with "saved": 16
```

With Docker: `docker build -t wjmax-server .` and `docker run --env-file .env -p 8000:8000 wjmax-server`, with `127.0.0.1` in `.env` changed to `host.docker.internal` so the container reaches the MySQL container.

Tests: `pip install -r requirements-dev.txt` and `python -m pytest -q`. Set `TEST_DATABASE_URL` to an empty MySQL database whose name ends in `test` to run them on MySQL as well; the tests drop and recreate the tables there and refuse any other database name.

## 한국어

우왁굳 팬게임 **왁제이맥스(WJMAX)**의 플레이 로그 수집 API입니다. 사이드 프로젝트(2023.08 ~ 2024.02, 2인 팀)로, 게임은 메인 개발자가 만들고 저는 서버를 단독으로 맡아 서버·보안 계층·데이터베이스를 담당했습니다. 동시 접속은 평균 약 300명, 업데이트 날 최대 약 2,000명이었습니다.

운영 구성: **게임 클라이언트 → Cloudflare(프록시, WAF) → AWS EC2(Docker의 FastAPI) → AWS RDS(MySQL)**.

이 저장소는 서비스 API를 2026년 10월에 정리해 다시 쓴 것입니다. 게임 클라이언트가 보내는 요청은 그대로입니다.

- **요청 하나에 트랜잭션 하나**: 보고 하나는 전부 저장되거나 전혀 저장되지 않습니다. 입력은 DB 연결을 잡기 전에 검사하므로, DB가 내려가 있어도 잘못된 입력은 `422`가 됩니다.
- **기기는 한 번만 등록**: 첫 보고에서 기기를 만들고(`INSERT IGNORE`), 이후 보고는 처음 본 시각을 유지합니다.
- **조회는 보고당 한 번**: 보고에 담긴 모든 곡의 첫 차트 키를 그룹 쿼리 하나로 가져옵니다.
- **작업 스레드마다 연결 하나**: FastAPI는 요청을 작업 스레드 40개 중 하나에서 실행합니다. 요청은 입력 검사가 끝난 뒤 그 스레드 안에서 연결을 잡고, 커넥션 풀은 연결을 40개까지 열 수 있어 연결을 기다리는 요청이 없습니다. 이 재작성의 이전 버전은 연결을 FastAPI 의존성으로 잡아 풀이 고갈됐고, 로컬 부하 테스트에서 클라이언트 60개가 동시에 보내자 요청 600개 중 281개가 풀 타임아웃으로 실패했습니다.
- **보고마다 한 행**: `report_tb`에 보고를 `(device_id, report_id)`와 서버가 받은 시각(`reported_at`)으로 남기고, 플레이 횟수 행은 모두 자기 보고를 가리킵니다. 그래서 한 기기의 스냅숏을 서로 구분하고 순서대로 볼 수 있습니다.
- **재전송은 한 번만 저장**: 클라이언트가 `report_id`를 보내면, 같은 id로 다시 온 보고는 아무것도 쓰지 않고 `"duplicate": true`로 답합니다. 두 번이 동시에 와도 키 때문에 두 번째 `INSERT IGNORE`가 첫 번째를 기다립니다. 배포된 게임 클라이언트는 id를 보내지 않으므로 서버가 id를 붙이고, 그 재전송은 별개의 보고로 저장됩니다. 이미 쓴 `report_id`가 다른 플레이 횟수와 함께 오면 `409`로 거절합니다. `report_tb`에 파싱한 플레이 횟수의 SHA-256을 남겨 두므로, 따옴표 방식이 달라도 같은 보고의 재전송은 재전송으로 인식합니다.
- **항목은 받은 그대로 저장**: 한 보고에 같은 곡이 두 번 있으면 그 보고 아래에 두 번 저장합니다([`client.py`](client.py)는 같은 곡을 가리키는 "Oort Cloud"와 별칭 "오르트 구름"을 함께 보냅니다). 횟수를 더할지, 하나만 남길지는 서버가 짐작하지 않고 데이터를 읽는 쪽에 맡깁니다.
- **입력 검증**: `count_log`는 파싱 전에 토큰 단위로 검사해 객체·리스트·문자열·숫자·키워드만, 최대 4단계 중첩까지 받습니다. 그래서 악의적인 입력도 JSON·Python 파서 안에서 죽지 않고 `422`가 됩니다. 각 항목은 공백이 아닌 곡 제목과 ASCII 숫자로 쓴, MySQL `INT`에 들어가는 횟수 8개여야 합니다. 1MB가 넘는 요청 본문은 `413`으로 거절합니다. `Content-Length`가 있으면 바로, 청크 전송이면 1MB를 넘는 순간 거절합니다. `music_tb`에 없는 곡은 건너뛰고 `unknown_titles`로 돌려줍니다. `device_id`는 로그에 그대로 남으므로 공백·줄바꿈·제어 문자를 받지 않습니다. 올바른 유니코드가 아닌 텍스트(짝 없는 서로게이트)는 `422`이고, `422` 응답은 필드와 문제만 알리고 입력을 되돌려 보내지 않습니다.
- **정확한 비교**: 곡 제목과 id는 바이트 그대로 비교합니다(`utf8mb4_0900_bin`). MySQL 기본 콜레이션은 대소문자·악센트·가나 차이를 무시해서 "Glory"와 "GLORY", "ゆめ"와 "ユメ"를 같은 곡으로 보고, `R-1` 보고를 `r-1`의 재전송으로 처리하기 때문입니다.
- **인증 없음**: 배포된 게임 클라이언트가 인증 정보를 보내지 않으므로, URL을 알면 누구나 아무 `device_id`로 보고를 보낼 수 있습니다. 입력 검증, 본문 크기 제한, 앞단의 Cloudflare가 남용을 막는 장치이고, 보고가 실제 플레이를 증명하지는 않습니다.
- **DB 없이도 시작**: 테이블은 코드와 [`schema.sql`](schema.sql)에 선언하고, 엔진은 처음 쓸 때 만들며, 오래된 연결은 쓰기 전에 확인합니다. `GET /healthz`는 DB 문제를 `503`으로 알립니다.
- **이미지에 비밀값 없음**: 설정은 실행할 때 환경 변수로 받고, 컨테이너는 root가 아닌 사용자로 돌며, API 문서는 `ENABLE_DOCS=1`일 때만 엽니다.
- **테스트**: [`tests/`](tests/)의 파싱·API 테스트를 GitHub Actions가 push마다 SQLite와, `schema.sql`로 만든 MySQL 8.0·8.4에서 각각 돌립니다. MySQL 쪽은 `schema.sql`이 코드와 맞는지, 제목과 id를 정확히 비교하는지, 동시에 온 재전송이 한 번만 저장되는지, 클라이언트 60개가 동시에 보내도 모두 응답받는지도 확인하고, 건너뛴 테스트가 하나라도 있으면 실패합니다.

오류 응답: 잘못된 입력은 `422`, 다른 플레이 횟수와 함께 재사용한 `report_id`는 `409`, 1MB가 넘는 본문은 `413`입니다.

실행 방법은 위의 [Run](#run)과 같습니다. Docker로 띄운 MySQL에 `schema.sql`과 샘플 곡 하나(`seed.sql`)를 넣고, `.env`의 설정을 export한 뒤 uvicorn을 실행합니다.
