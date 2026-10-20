-- MySQL 8 schema for the tables the API writes to (the same tables app/db_session.py declares).
-- music_tb holds one row per chart; each song's eight charts have consecutive keys.
--
-- Titles and ids compare exactly (utf8mb4_0900_bin). MySQL's default utf8mb4_0900_ai_ci ignores
-- case, accents and kana, so "Glory" and "GLORY", "Cafe" and "Café", or "ゆめ" and "ユメ" would be one
-- song, and report "R-1" would count as a retry of "r-1". The _0900_ collation does not pad, so a
-- trailing space is a difference too.

CREATE TABLE IF NOT EXISTS user_tb (
    device_id   VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL PRIMARY KEY,
    insert_date DATETIME    NOT NULL COMMENT 'first report from the device, UTC'
) DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS music_tb (
    music_key INT          NOT NULL PRIMARY KEY,
    name      VARCHAR(100) COLLATE utf8mb4_0900_bin NOT NULL,
    INDEX ix_music_tb_name (name)
) DEFAULT CHARSET=utf8mb4;

-- one row per report; a retry with the same (device_id, report_id) is not stored again, and the same
-- id sent with other play counts is refused
CREATE TABLE IF NOT EXISTS report_tb (
    device_id     VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL,
    report_id     VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL COMMENT 'sent by the client, or a UUID when it sends none',
    reported_at   DATETIME(6) NOT NULL COMMENT 'when the server received the report, UTC',
    counts_sha256 CHAR(64)    NOT NULL COMMENT 'SHA-256 of the parsed play counts, to tell a retry from a reused id',
    PRIMARY KEY (device_id, report_id),
    FOREIGN KEY (device_id) REFERENCES user_tb (device_id)
) DEFAULT CHARSET=utf8mb4;

-- play-count snapshots, one row per chart per report
CREATE TABLE IF NOT EXISTS playcount_tb (
    id        BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL,
    report_id VARCHAR(64) COLLATE utf8mb4_0900_bin NOT NULL,
    music_key INT         NOT NULL,
    count     INT         NOT NULL,
    INDEX ix_playcount_tb_report (device_id, report_id),
    FOREIGN KEY (device_id, report_id) REFERENCES report_tb (device_id, report_id)
) DEFAULT CHARSET=utf8mb4;
