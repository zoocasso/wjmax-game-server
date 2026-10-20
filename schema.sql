-- MySQL schema for the three tables the API writes to, reconstructed from the code.
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

CREATE TABLE IF NOT EXISTS playcount_tb (
    device_id VARCHAR(64) NOT NULL,
    music_key INT         NOT NULL,
    count     INT         NOT NULL,
    INDEX ix_playcount_tb_device_id (device_id)
);
