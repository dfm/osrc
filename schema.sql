DROP TABLE IF EXISTS osrc_status CASCADE;
CREATE TABLE osrc_status (
    status_id      integer PRIMARY KEY,
    last_id        bigint,
    last_updated   timestamp,
    etag           text
);

DROP TABLE IF EXISTS gh_users CASCADE;
CREATE TABLE gh_users (
    user_id        bigint PRIMARY KEY,
    user_type      text,
    name           text,
    login          text,
    bio            text,
    location       text,
    avatar_url     text,
    tz             integer,
    active         boolean DEFAULT TRUE,
    etag           text
);

DROP TABLE IF EXISTS gh_repos CASCADE;
CREATE TABLE gh_repos (
    repo_id        bigint PRIMARY KEY,
    owner_id       bigint REFERENCES gh_users(user_id),
    name           text,
    description    text,
    language       text,
    star_count     integer,    /* stargazers_count */
    watcher_count  integer,    /* subscribers_count */
    fork_count     integer,    /* forks_count */
    issue_count    integer,    /* open_issues_count */
    updated        timestamp,  /* updated_at */
    active         boolean DEFAULT TRUE,
    etag           text
);

DROP TABLE IF EXISTS gh_event_stats CASCADE;
CREATE TABLE gh_event_stats (
    user_id        bigint REFERENCES gh_users(user_id),
    repo_id        bigint REFERENCES gh_repos(repo_id),
    evttype        text,
    count          integer DEFAULT 1,
    last_modified  timestamp,
    CONSTRAINT user_repo_evt PRIMARY KEY(user_id, repo_id, evttype)
);

DROP TABLE IF EXISTS gh_event_days CASCADE;
CREATE TABLE gh_event_days (
    user_id        bigint REFERENCES gh_users(user_id),
    evttype        text,
    day            integer,
    count          integer DEFAULT 1,
    CONSTRAINT user_evt_day PRIMARY KEY(user_id, evttype, day)
);

DROP TABLE IF EXISTS gh_event_hours CASCADE;
CREATE TABLE gh_event_hours (
    user_id        bigint REFERENCES gh_users(user_id),
    evttype        text,
    hour           integer,
    count          integer DEFAULT 1,
    CONSTRAINT user_evt_hour PRIMARY KEY(user_id, evttype, hour)
);
