import re
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import bindparam, text
from db import make_engine

HERE = Path(__file__).resolve().parent
SCHEMA_FILE = HERE / "schema.sql"
SEED_FILE = HERE / "seed.sql"

FULL_NAME = "CONCAT({a}.given_name, ' ', {a}.surname)"

ROW_COUNTS = """
SELECT 'app_user' AS table_name, COUNT(*) AS row_count FROM app_user
UNION ALL SELECT 'author', COUNT(*) FROM author
UNION ALL SELECT 'author_research_area', COUNT(*) FROM author_research_area
UNION ALL SELECT 'reviewer', COUNT(*) FROM reviewer
UNION ALL SELECT 'reviewer_expertise', COUNT(*) FROM reviewer_expertise
UNION ALL SELECT 'conference', COUNT(*) FROM conference
UNION ALL SELECT 'conference_host', COUNT(*) FROM conference_host
UNION ALL SELECT 'conference_reviewer', COUNT(*) FROM conference_reviewer
UNION ALL SELECT 'track', COUNT(*) FROM track
UNION ALL SELECT 'conference_session', COUNT(*) FROM conference_session
UNION ALL SELECT 'paper', COUNT(*) FROM paper
UNION ALL SELECT 'paper_keyword', COUNT(*) FROM paper_keyword
UNION ALL SELECT 'paper_author', COUNT(*) FROM paper_author
UNION ALL SELECT 'paper_version', COUNT(*) FROM paper_version
UNION ALL SELECT 'review', COUNT(*) FROM review
"""

Q3_1_SHOW = """
SELECT user_id, given_name, surname, email, phone_number
FROM app_user
WHERE email = :email
"""
Q3_1_UPDATE = """
UPDATE app_user
SET phone_number = :phone
WHERE email = :email
"""
Q3_2_SHOW = """
SELECT conference_id, acronym, city, review_deadline
FROM conference
ORDER BY conference_id
"""
Q3_2_UPDATE = """
UPDATE conference
SET review_deadline = CASE
        WHEN city = :city THEN DATE_ADD(review_deadline, INTERVAL :days_city DAY)
        ELSE DATE_ADD(review_deadline, INTERVAL :days_other DAY)
    END
"""

Q4_1_TARGETS = """
SELECT p.paper_id, p.title, p.status
FROM paper p
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding = TRUE
JOIN app_user u      ON u.user_id = pa.author_id
WHERE p.status = :status
  AND u.email = :email
ORDER BY p.paper_id
"""
Q4_1_DEPENDENTS = """
SELECT
  (SELECT COUNT(*) FROM paper         WHERE paper_id IN :ids) AS papers,
  (SELECT COUNT(*) FROM paper_author  WHERE paper_id IN :ids) AS authorship_rows,
  (SELECT COUNT(*) FROM paper_keyword WHERE paper_id IN :ids) AS keyword_rows,
  (SELECT COUNT(*) FROM paper_version WHERE paper_id IN :ids) AS version_rows,
  (SELECT COUNT(*) FROM review        WHERE paper_id IN :ids) AS review_rows
"""
Q4_1_DELETE = """
DELETE FROM paper
WHERE paper_id IN :ids
"""
Q4_1_KEPT = """
SELECT
  (SELECT COUNT(*) FROM app_user)   AS users,
  (SELECT COUNT(*) FROM track)      AS tracks,
  (SELECT COUNT(*) FROM conference) AS conferences,
  (SELECT COUNT(*) FROM paper)      AS papers,
  (SELECT COUNT(*) FROM app_user WHERE email = :email) AS amina_still_exists
"""
Q4_1_WITHDRAWN = """
SELECT paper_id, title, status
FROM paper
WHERE status = :status
ORDER BY paper_id
"""
Q4_2_SHOW = """
SELECT s.session_id, s.title, c.acronym, c.city, COUNT(p.paper_id) AS assigned_papers
FROM conference_session s
JOIN conference c  ON c.conference_id = s.conference_id
LEFT JOIN paper p  ON p.session_id = s.session_id
GROUP BY s.session_id, s.title, c.acronym, c.city
ORDER BY s.session_id
"""
Q4_2_DELETE = """
DELETE s
FROM conference_session s
JOIN conference c ON c.conference_id = s.conference_id
WHERE c.city = :city
  AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)
"""
Q4_2_CONFERENCES = "SELECT COUNT(*) AS conferences FROM conference"

Q5_1 = f"""
SELECT p.paper_id, p.title,
       {FULL_NAME.format(a='u')} AS corresponding_author, u.email,
       t.name AS track_name, c.conference_id, c.acronym
FROM paper p
JOIN track t         ON t.track_id = p.track_id
JOIN conference c    ON c.conference_id = t.conference_id
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding = TRUE
JOIN app_user u      ON u.user_id = pa.author_id
WHERE p.status = :status
ORDER BY p.paper_id
"""
Q5_2 = """
SELECT paper_id, title
FROM paper
WHERE LOWER(abstract) LIKE CONCAT('%', LOWER(:phrase), '%')
ORDER BY paper_id
"""
Q5_3 = """
SELECT version_no, file_location, uploaded_at
FROM paper_version
WHERE paper_id = :paper_id
ORDER BY version_no DESC
"""
Q5_4 = f"""
SELECT DISTINCT r.reviewer_id, {FULL_NAME.format(a='u')} AS full_name, u.email
FROM conference_reviewer cr
JOIN reviewer r            ON r.reviewer_id = cr.reviewer_id
JOIN reviewer_expertise re ON re.reviewer_id = r.reviewer_id
JOIN app_user u            ON u.user_id = r.reviewer_id
WHERE cr.conference_id = :conference_id
  AND re.area_label = :area
  AND r.years_experience >= :min_years
ORDER BY r.reviewer_id
"""

Q6_1 = """
SELECT t.track_id, t.name, t.conference_id,
       COUNT(DISTINCT p.paper_id)   AS paper_count,
       COUNT(DISTINCT pa.author_id) AS author_count
FROM track t
LEFT JOIN paper p         ON p.track_id = t.track_id
LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
GROUP BY t.track_id, t.name, t.conference_id
ORDER BY t.track_id
"""
Q6_2 = f"""
SELECT r.reviewer_id, {FULL_NAME.format(a='u')} AS full_name,
       COUNT(rv.review_id)            AS review_count,
       ROUND(AVG(rv.overall_score), 2) AS avg_overall_score
FROM reviewer r
JOIN app_user u     ON u.user_id = r.reviewer_id
LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
GROUP BY r.reviewer_id, u.given_name, u.surname
ORDER BY r.reviewer_id
"""
Q6_3 = """
SELECT c.conference_id, c.acronym,
       COALESCE(pc.total_papers, 0)    AS total_papers,
       COALESCE(pc.accepted_papers, 0) AS accepted_papers,
       rs.avg_overall_score
FROM conference c
LEFT JOIN (
    SELECT t.conference_id,
           COUNT(*) AS total_papers,
           SUM(CASE WHEN p.status = 'accepted' THEN 1 ELSE 0 END) AS accepted_papers
    FROM paper p
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
) pc ON pc.conference_id = c.conference_id
LEFT JOIN (
    SELECT t.conference_id, ROUND(AVG(r.overall_score), 2) AS avg_overall_score
    FROM review r
    JOIN paper p ON p.paper_id = r.paper_id
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
) rs ON rs.conference_id = c.conference_id
ORDER BY c.conference_id
"""
Q6_4 = f"""
WITH review_counts AS (
    SELECT r.reviewer_id, COUNT(rv.review_id) AS review_count
    FROM reviewer r
    LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id
),
overall AS (
    SELECT AVG(review_count) AS avg_reviews FROM review_counts
)
SELECT rc.reviewer_id, {FULL_NAME.format(a='u')} AS full_name,
       rc.review_count, ROUND(o.avg_reviews, 2) AS avg_reviews_per_reviewer
FROM review_counts rc
CROSS JOIN overall o
JOIN app_user u ON u.user_id = rc.reviewer_id
WHERE rc.review_count > o.avg_reviews
ORDER BY rc.review_count DESC, rc.reviewer_id
"""

Q7 = """
SELECT c.conference_id, c.acronym,
       SUM(CASE WHEN p.status = 'accepted' THEN 1 ELSE 0 END) AS accepted_count,
       SUM(CASE WHEN p.status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,
       ROUND(100.0 * SUM(CASE WHEN p.status = 'accepted' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN p.status IN ('accepted', 'rejected') THEN 1 ELSE 0 END), 0),
             2) AS acceptance_rate
FROM conference c
LEFT JOIN track t ON t.conference_id = c.conference_id
LEFT JOIN paper p ON p.track_id = t.track_id
GROUP BY c.conference_id, c.acronym
ORDER BY c.conference_id
"""

Q8_CREATE_VIEW = f"""
CREATE OR REPLACE VIEW accepted_paper_schedule AS
SELECT p.paper_id, p.title AS paper_title,
       c.conference_id, c.acronym,
       t.name AS track_name,
       s.session_id, s.title AS session_title,
       s.session_date, s.start_time, s.end_time, s.room_label,
       {FULL_NAME.format(a='ch')} AS chair_name,
       {FULL_NAME.format(a='ca')} AS corresponding_author, ca.email AS corresponding_email
FROM paper p
JOIN conference_session s ON s.session_id = p.session_id
JOIN track t              ON t.track_id = p.track_id
JOIN conference c         ON c.conference_id = s.conference_id
JOIN app_user ch          ON ch.user_id = s.chair_id
JOIN paper_author pa      ON pa.paper_id = p.paper_id AND pa.is_corresponding = TRUE
JOIN app_user ca          ON ca.user_id = pa.author_id
WHERE p.status = 'accepted'
"""
Q8_QUERY = """
SELECT *
FROM accepted_paper_schedule
ORDER BY conference_id, session_date, start_time, session_id, paper_id
"""

P = {
    "arman_email": "arman.armanov@example.com",
    "new_phone": "+77773414141",
    "amina_email": "amina.aminova@example.com",
    "city": "Astana",
    "phrase": "machine learning",
    "paper_id": 3,
    "conference_id": 1,
    "area": "Databases",
    "min_years": 3,
}

def heading(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, (date, datetime, time)):
        return v.isoformat()
    if isinstance(v, timedelta):
        total = int(v.total_seconds())
        return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
    return str(v)

def print_table(columns, rows, max_width=80):
    cells = [[fmt(v) for v in r] for r in rows]
    cells = [[c if len(c) <= max_width else c[: max_width - 3] + "..." for c in r] for r in cells]
    widths = [len(c) for c in columns]
    for r in cells:
        widths = [max(w, len(c)) for w, c in zip(widths, r)]
    line = "+".join("-" * (w + 2) for w in widths)
    print(" | ".join(c.ljust(w) for c, w in zip(columns, widths)))
    print(line)
    for r in cells:
        print(" | ".join(c.ljust(w) for c, w in zip(r, widths)))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")

def show_sql(sql, params=None):
    print("SQL:")
    print("\n".join("    " + line for line in sql.strip().splitlines()))
    if params:
        print(f"Parameters: {params}")

def run_query(conn, label, sql, params=None, expanding=()):
    print(f"\n--- {label} ---")
    show_sql(sql, params)
    stmt = text(sql)
    if expanding:
        stmt = stmt.bindparams(*[bindparam(name, expanding=True) for name in expanding])
    result = conn.execute(stmt, params or {})
    print("Result:")
    print_table(list(result.keys()), result.fetchall())

def run_change(conn, label, sql, params=None, expanding=()):
    print(f"\n--- {label} ---")
    show_sql(sql, params)
    stmt = text(sql)
    if expanding:
        stmt = stmt.bindparams(*[bindparam(name, expanding=True) for name in expanding])
    result = conn.execute(stmt, params or {})
    print(f"Rows affected: {result.rowcount}")

def sql_statements(path):
    body = re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))
    statements = [s.strip() for s in body.split(";") if s.strip()]
    return [s for s in statements if s.upper() not in ("START TRANSACTION", "COMMIT")]

def run_sql_file(engine, path):
    statements = sql_statements(path)
    with engine.begin() as conn:
        for s in statements:
            conn.execute(text(s))
    return statements

def task_1(engine):
    heading("TASK 1 - Create statements (schema.sql)")
    statements = run_sql_file(engine, SCHEMA_FILE)
    creates = [s for s in statements if s.upper().startswith("CREATE TABLE")]
    print(f"Executed {len(statements)} statements from {SCHEMA_FILE.name} "
          f"({len(creates)} CREATE TABLE). Example of an executed statement:\n")
    review = next(s for s in creates if "CREATE TABLE review (" in s)
    print(review)
    with engine.connect() as conn:
        run_query(conn, "1 Tables created",
                  "SELECT table_name FROM information_schema.tables "
                  "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' ORDER BY table_name")
        run_query(conn, "1 Constraints created",
                  "SELECT table_name, constraint_type, COUNT(*) AS how_many "
                  "FROM information_schema.table_constraints WHERE table_schema = DATABASE() "
                  "GROUP BY table_name, constraint_type ORDER BY table_name, constraint_type")

def task_2(engine):
    heading("TASK 2 - Insert statements (seed.sql)")
    statements = run_sql_file(engine, SEED_FILE)
    print(f"Executed {len(statements)} INSERT statements from {SEED_FILE.name}.")
    print("To restore the initial dataset: run this program again, or run schema.sql and then seed.sql with the mysql client.")
    with engine.connect() as conn:
        run_query(conn, "2 Row count of every table", ROW_COUNTS)

def task_3(engine):
    heading("TASK 3.1 - Update the phone number of Arman Armanov")
    params = {"email": P["arman_email"], "phone": P["new_phone"]}
    with engine.connect() as conn:
        tx = conn.begin()
        run_query(conn, "3.1 BEFORE", Q3_1_SHOW, {"email": params["email"]})
        run_change(conn, "3.1 UPDATE", Q3_1_UPDATE, params)
        run_query(conn, "3.1 AFTER", Q3_1_SHOW, {"email": params["email"]})
        tx.rollback()
        print("Transaction rolled back - seed data restored.")

    heading("TASK 3.2 - Extend review deadlines (+7 days Astana, +3 days otherwise)")
    params = {"city": P["city"], "days_city": 7, "days_other": 3}
    with engine.connect() as conn:
        tx = conn.begin()
        run_query(conn, "3.2 BEFORE", Q3_2_SHOW)
        run_change(conn, "3.2 UPDATE (single conditional UPDATE)", Q3_2_UPDATE, params)
        run_query(conn, "3.2 AFTER", Q3_2_SHOW)
        tx.rollback()
        print("Transaction rolled back - seed data restored.")

def task_4(engine):
    heading("TASK 4.1 - Delete withdrawn papers whose corresponding author is Amina Aminova")
    target_params = {"status": "withdrawn", "email": P["amina_email"]}
    with engine.connect() as conn:
        tx = conn.begin()
        run_query(conn, "4.1 Papers to delete", Q4_1_TARGETS, target_params)
        ids = [r.paper_id for r in conn.execute(text(Q4_1_TARGETS), target_params)]
        dep = {"ids": ids}
        run_query(conn, "4.1 BEFORE - rows of these papers", Q4_1_DEPENDENTS, dep, ("ids",))
        run_query(conn, "4.1 BEFORE - all withdrawn papers", Q4_1_WITHDRAWN, {"status": "withdrawn"})
        run_query(conn, "4.1 BEFORE - records that must be kept", Q4_1_KEPT, {"email": P["amina_email"]})
        run_change(conn, "4.1 DELETE (authorship, keywords, versions, reviews removed by ON DELETE CASCADE)", Q4_1_DELETE, dep, ("ids",))
        run_query(conn, "4.1 AFTER - rows of these papers", Q4_1_DEPENDENTS, dep, ("ids",))
        run_query(conn, "4.1 AFTER - all withdrawn papers", Q4_1_WITHDRAWN, {"status": "withdrawn"})
        run_query(conn, "4.1 AFTER - records that must be kept", Q4_1_KEPT, {"email": P["amina_email"]})
        tx.rollback()
        print("Transaction rolled back - seed data restored.")

    heading("TASK 4.2 - Delete empty sessions of conferences held in Astana")
    with engine.connect() as conn:
        tx = conn.begin()
        run_query(conn, "4.2 BEFORE - sessions", Q4_2_SHOW)
        run_query(conn, "4.2 BEFORE - conferences", Q4_2_CONFERENCES)
        run_change(conn, "4.2 DELETE", Q4_2_DELETE, {"city": P["city"]})
        run_query(conn, "4.2 AFTER - sessions", Q4_2_SHOW)
        run_query(conn, "4.2 AFTER - conferences", Q4_2_CONFERENCES)
        tx.rollback()
        print("Transaction rolled back - seed data restored.")

def task_5(engine):
    with engine.connect() as conn:
        heading("TASK 5.1 - Accepted papers with corresponding author, track and conference")
        run_query(conn, "5.1", Q5_1, {"status": "accepted"})
        heading("TASK 5.2 - Papers whose abstract contains 'machine learning' (case-insensitive)")
        run_query(conn, "5.2", Q5_2, {"phrase": P["phrase"]})
        heading(f"TASK 5.3 - Versions of paper {P['paper_id']}, newest first")
        run_query(conn, "5.3", Q5_3, {"paper_id": P["paper_id"]})
        heading(f"TASK 5.4 - Databases reviewers with >= 3 years in conference {P['conference_id']}'s pool")
        run_query(conn, "5.4", Q5_4, {"conference_id": P["conference_id"], "area": P["area"], "min_years": P["min_years"]})

def task_6(engine):
    with engine.connect() as conn:
        heading("TASK 6.1 - Papers and distinct authors per track")
        run_query(conn, "6.1", Q6_1)
        heading("TASK 6.2 - Completed reviews and average score per reviewer")
        run_query(conn, "6.2", Q6_2)
        heading("TASK 6.3 - Papers, accepted papers and average review score per conference")
        run_query(conn, "6.3", Q6_3)
        heading("TASK 6.4 - Reviewers with more reviews than the average per reviewer")
        run_query(conn, "6.4", Q6_4)

def task_7(engine):
    with engine.connect() as conn:
        heading("TASK 7 - Acceptance rate per conference (derived attribute)")
        run_query(conn, "7", Q7)

def task_8(engine):
    heading("TASK 8 - View accepted_paper_schedule")
    with engine.begin() as conn:
        print("\n--- 8 CREATE VIEW ---")
        show_sql(Q8_CREATE_VIEW)
        conn.execute(text(Q8_CREATE_VIEW))
        print("View created.")
    with engine.connect() as conn:
        run_query(conn, "8 Query the view", Q8_QUERY)
        run_query(conn, "8 Proof it is a VIEW (not a table)",
                  "SELECT table_name, table_type FROM information_schema.tables "
                  "WHERE table_schema = DATABASE() AND table_name = :name",
                  {"name": "accepted_paper_schedule"})

def main():
    engine = make_engine()
    print(f"Connecting to {engine.url.render_as_string(hide_password=True)}")
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
    print(f"Connected. MySQL server version: {version}")

    task_1(engine)
    task_2(engine)
    task_3(engine)
    task_4(engine)
    task_5(engine)
    task_6(engine)
    task_7(engine)
    task_8(engine)
    print("\nAll tasks finished. The database contains the original seed data and the view.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)