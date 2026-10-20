-- MySQL schema for the tables the API writes to (the same tables app/db_session.py declares).
-- music_tb holds one row per chart; each song's eight charts have consecutive keys.

CREATE TABLE IF NOT EXISTS user_tb (
    device_id   VARCHAR(64) NOT NULL PRIMARY KEY,
    insert_date DATETIME    NOT NULL COMMENT 'first report from the device, UTC'
);

CREATE TABLE IF NOT EXISTS music_tb (
    music_key INT          NOT NULL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    INDEX ix_music_tb_name (name)
);

-- one row per report; a retry with the same (device_id, report_id) is not stored again
CREATE TABLE IF NOT EXISTS report_tb (
    device_id   VARCHAR(64) NOT NULL,
    report_id   VARCHAR(64) NOT NULL COMMENT 'sent by the client, or a UUID when it sends none',
    reported_at DATETIME(6) NOT NULL COMMENT 'when the server received the report, UTC',
    PRIMARY KEY (device_id, report_id),
    FOREIGN KEY (device_id) REFERENCES user_tb (device_id)
);

-- play-count snapshots, one row per chart per report
CREATE TABLE IF NOT EXISTS playcount_tb (
    id        BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    report_id VARCHAR(64) NOT NULL,
    music_key INT         NOT NULL,
    count     INT         NOT NULL,
    INDEX ix_playcount_tb_report (device_id, report_id),
    FOREIGN KEY (device_id, report_id) REFERENCES report_tb (device_id, report_id)
);
