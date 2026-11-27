DROP VIEW  IF EXISTS accepted_paper_schedule;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS paper_version;
DROP TABLE IF EXISTS paper_author;
DROP TABLE IF EXISTS paper_keyword;
DROP TABLE IF EXISTS paper;
DROP TABLE IF EXISTS conference_session;
DROP TABLE IF EXISTS track;
DROP TABLE IF EXISTS conference_reviewer;
DROP TABLE IF EXISTS conference_host;
DROP TABLE IF EXISTS conference;
DROP TABLE IF EXISTS reviewer_expertise;
DROP TABLE IF EXISTS reviewer;
DROP TABLE IF EXISTS author_research_area;
DROP TABLE IF EXISTS author;
DROP TABLE IF EXISTS app_user;

CREATE TABLE app_user (
    user_id       INT           NOT NULL AUTO_INCREMENT,
    given_name    VARCHAR(100)  NOT NULL,
    surname       VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  NOT NULL,
    affiliation   VARCHAR(200)  NOT NULL,
    country       VARCHAR(100)  NOT NULL,
    phone_number  VARCHAR(30)   NOT NULL,
    CONSTRAINT pk_app_user        PRIMARY KEY (user_id),
    CONSTRAINT uq_app_user_email  UNIQUE (email),
    CONSTRAINT chk_app_user_email CHECK (email LIKE '%_@_%._%')
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE author (
    author_id  INT          NOT NULL,
    orcid      VARCHAR(19)  NULL,
    CONSTRAINT pk_author       PRIMARY KEY (author_id),
    CONSTRAINT uq_author_orcid UNIQUE (orcid),
    CONSTRAINT fk_author_user  FOREIGN KEY (author_id)
        REFERENCES app_user (user_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE author_research_area (
    author_id   INT          NOT NULL,
    area_label  VARCHAR(100) NOT NULL,
    CONSTRAINT pk_author_research_area PRIMARY KEY (author_id, area_label),
    CONSTRAINT fk_ara_author FOREIGN KEY (author_id)
        REFERENCES author (author_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE reviewer (
    reviewer_id       INT NOT NULL,
    years_experience  INT NOT NULL,
    CONSTRAINT pk_reviewer      PRIMARY KEY (reviewer_id),
    CONSTRAINT chk_reviewer_exp CHECK (years_experience >= 0),
    CONSTRAINT fk_reviewer_user FOREIGN KEY (reviewer_id)
        REFERENCES app_user (user_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE reviewer_expertise (
    reviewer_id INT          NOT NULL,
    area_label  VARCHAR(100) NOT NULL,
    CONSTRAINT pk_reviewer_expertise PRIMARY KEY (reviewer_id, area_label),
    CONSTRAINT fk_re_reviewer FOREIGN KEY (reviewer_id)
        REFERENCES reviewer (reviewer_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE conference (
    conference_id        INT          NOT NULL AUTO_INCREMENT,
    name                 VARCHAR(200) NOT NULL,
    acronym              VARCHAR(30)  NOT NULL,
    description          TEXT         NOT NULL,
    city                 VARCHAR(100) NOT NULL,
    country              VARCHAR(100) NOT NULL,
    start_date           DATE         NOT NULL,
    end_date             DATE         NOT NULL,
    submission_deadline  DATE         NOT NULL,
    review_deadline      DATE         NOT NULL,
    CONSTRAINT pk_conference         PRIMARY KEY (conference_id),
    CONSTRAINT uq_conference_acronym UNIQUE (acronym),
    CONSTRAINT chk_conference_dates  CHECK (end_date >= start_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE conference_host (
    conference_id INT          NOT NULL,
    host_name     VARCHAR(200) NOT NULL,
    CONSTRAINT pk_conference_host PRIMARY KEY (conference_id, host_name),
    CONSTRAINT fk_ch_conference FOREIGN KEY (conference_id)
        REFERENCES conference (conference_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE conference_reviewer (
    conference_id INT NOT NULL,
    reviewer_id   INT NOT NULL,
    CONSTRAINT pk_conference_reviewer PRIMARY KEY (conference_id, reviewer_id),
    CONSTRAINT fk_cr_conference FOREIGN KEY (conference_id)
        REFERENCES conference (conference_id) ON DELETE CASCADE,
    CONSTRAINT fk_cr_reviewer FOREIGN KEY (reviewer_id)
        REFERENCES reviewer (reviewer_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE track (
    track_id        INT          NOT NULL AUTO_INCREMENT,
    conference_id   INT          NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT         NOT NULL,
    research_area   VARCHAR(100) NOT NULL,
    coordinator_id  INT          NOT NULL,
    CONSTRAINT pk_track          PRIMARY KEY (track_id),
    CONSTRAINT uq_track_name     UNIQUE (conference_id, name),
    CONSTRAINT fk_track_conference FOREIGN KEY (conference_id)
        REFERENCES conference (conference_id) ON DELETE RESTRICT,
    CONSTRAINT fk_track_coordinator FOREIGN KEY (coordinator_id)
        REFERENCES reviewer (reviewer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_track_coordinator_pool FOREIGN KEY (conference_id, coordinator_id)
        REFERENCES conference_reviewer (conference_id, reviewer_id) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE conference_session (
    session_id     INT          NOT NULL AUTO_INCREMENT,
    conference_id  INT          NOT NULL,
    title          VARCHAR(200) NOT NULL,
    session_date   DATE         NOT NULL,
    start_time     TIME         NOT NULL,
    end_time       TIME         NOT NULL,
    room_label     VARCHAR(50)  NOT NULL,
    chair_id       INT          NOT NULL,
    CONSTRAINT pk_conference_session PRIMARY KEY (session_id),
    CONSTRAINT chk_session_times     CHECK (end_time > start_time),
    CONSTRAINT fk_session_conference FOREIGN KEY (conference_id)
        REFERENCES conference (conference_id) ON DELETE RESTRICT,
    CONSTRAINT fk_session_chair FOREIGN KEY (chair_id)
        REFERENCES reviewer (reviewer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_session_chair_pool FOREIGN KEY (conference_id, chair_id)
        REFERENCES conference_reviewer (conference_id, reviewer_id) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE paper (
    paper_id         INT          NOT NULL AUTO_INCREMENT,
    track_id         INT          NOT NULL,
    title            VARCHAR(300) NOT NULL,
    abstract         TEXT         NOT NULL,
    submission_date  DATE         NOT NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'submitted',
    session_id       INT          NULL,
    CONSTRAINT pk_paper        PRIMARY KEY (paper_id),
    CONSTRAINT chk_paper_status CHECK (status IN
        ('submitted', 'under review', 'accepted', 'rejected', 'withdrawn')),
    CONSTRAINT fk_paper_track FOREIGN KEY (track_id)
        REFERENCES track (track_id) ON DELETE RESTRICT,
    CONSTRAINT fk_paper_session FOREIGN KEY (session_id)
        REFERENCES conference_session (session_id) ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE paper_keyword (
    paper_id INT          NOT NULL,
    keyword  VARCHAR(100) NOT NULL,
    CONSTRAINT pk_paper_keyword PRIMARY KEY (paper_id, keyword),
    CONSTRAINT fk_pk_paper FOREIGN KEY (paper_id)
        REFERENCES paper (paper_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE paper_author (
    paper_id          INT        NOT NULL,
    author_id         INT        NOT NULL,
    author_position   INT        NOT NULL,
    is_corresponding  BOOLEAN    NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_paper_author       PRIMARY KEY (paper_id, author_id),
    CONSTRAINT uq_paper_author_pos   UNIQUE (paper_id, author_position),
    CONSTRAINT chk_paper_author_pos  CHECK (author_position > 0),
    CONSTRAINT fk_pa_paper FOREIGN KEY (paper_id)
        REFERENCES paper (paper_id) ON DELETE CASCADE,
    CONSTRAINT fk_pa_author FOREIGN KEY (author_id)
        REFERENCES author (author_id) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE paper_version (
    paper_id       INT          NOT NULL,
    version_no     INT          NOT NULL,
    file_location  VARCHAR(500) NOT NULL,
    uploaded_at    DATETIME     NOT NULL,
    change_note    TEXT         NULL,
    CONSTRAINT pk_paper_version     PRIMARY KEY (paper_id, version_no),
    CONSTRAINT chk_paper_version_no CHECK (version_no > 0),
    CONSTRAINT fk_pv_paper FOREIGN KEY (paper_id)
        REFERENCES paper (paper_id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE review (
    review_id               INT         NOT NULL AUTO_INCREMENT,
    paper_id                INT         NOT NULL,
    reviewer_id             INT         NOT NULL,
    overall_score           INT         NOT NULL,
    recommendation          VARCHAR(10) NOT NULL,
    comments_for_authors    TEXT        NOT NULL,
    confidential_comments   TEXT        NULL,
    review_submission_date  DATE        NOT NULL,
    CONSTRAINT pk_review                PRIMARY KEY (review_id),
    CONSTRAINT uq_review_paper_reviewer UNIQUE (paper_id, reviewer_id),
    CONSTRAINT chk_review_score         CHECK (overall_score BETWEEN 1 AND 5),
    CONSTRAINT chk_review_recommendation CHECK (recommendation IN ('accept', 'reject')),
    CONSTRAINT chk_review_comments      CHECK (CHAR_LENGTH(comments_for_authors) > 0),
    CONSTRAINT fk_review_paper FOREIGN KEY (paper_id)
        REFERENCES paper (paper_id) ON DELETE CASCADE,
    CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id)
        REFERENCES reviewer (reviewer_id) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
