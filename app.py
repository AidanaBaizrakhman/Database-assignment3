import os
import re
from datetime import date, datetime, time, timedelta
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from db import make_engine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
engine = make_engine()

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
RECOMMENDATIONS = ["accept", "reject"]

class AppError(Exception):
    """"""

def rows(sql, **params):
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(sql), params).mappings()]

def one(sql, **params):
    result = rows(sql, **params)
    return result[0] if result else None

def run(conn, sql, **params):
    return conn.execute(text(sql), params)

def value(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()

FRIENDLY = {
    "uq_app_user_email": "This email is already used by another user.",
    "chk_app_user_email": "The email address is not valid.",
    "uq_author_orcid": "This ORCID is already used by another author.",
    "chk_reviewer_exp": "Years of reviewing experience cannot be negative.",
    "paper_author.PRIMARY": "This person is already an author of this paper.",
    "uq_paper_author_pos": "Another author of this paper already has this position.",
    "chk_paper_author_pos": "Author position must be a positive whole number.",
    "paper_keyword.PRIMARY": "This paper already has that keyword.",
    "paper_version.PRIMARY": "This paper already has a version with that number.",
    "chk_paper_version_no": "Version number must be a positive whole number.",
    "chk_paper_status": "Invalid paper status.",
    "uq_review_paper_reviewer": "This reviewer has already reviewed this paper (one review per reviewer and paper).",
    "chk_review_score": "Overall score must be a whole number from 1 to 5.",
    "chk_review_recommendation": "Recommendation must be 'accept' or 'reject'.",
    "chk_review_comments": "Comments for authors are required.",
    "chk_session_times": "Session end time must be later than its start time.",
    "fk_session_chair_pool": "The session chair must be in the reviewer pool of the session's conference ",
    "fk_track_coordinator_pool": "A track coordinator cannot be removed from that conference's reviewer pool.",
    "fk_session_chair": "This reviewer chairs a session. Choose another chair for that session first.",
    "fk_track_coordinator": "This reviewer coordinates a track and cannot lose the reviewer role.",
    "fk_pa_author": "This user is an author of at least one paper. Remove them from those papers first.",
    "fk_review_reviewer": "This reviewer has written reviews. Delete those reviews first.",
}

def explain(error):
    message = str(getattr(error, "orig", error))
    for key in sorted(FRIENDLY, key=len, reverse=True):
        if key in message:
            return FRIENDLY[key]
    return "The database rejected the change: " + message

def attempt(action, success_message):
    try:
        with engine.begin() as conn:
            result = action(conn)
        flash(success_message, "success")
        return True, result
    except AppError as e:
        flash(str(e), "error")
    except DBAPIError as e:
        flash(explain(e), "error")
    return False, None

def field(name):
    return request.form.get(name, "").strip()

def required(name, label):
    v = field(name)
    if not v:
        raise AppError(f"{label} is required.")
    return v

def integer(name, label, optional=False):
    v = field(name)
    if not v:
        if optional:
            return None
        raise AppError(f"{label} is required.")
    try:
        return int(v)
    except ValueError:
        raise AppError(f"{label} must be a whole number.")

def label_list(name):
    seen, out = set(), []
    for part in re.split(r"[,\n]", request.form.get(name, "")):
        p = part.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out

@app.template_filter("hm")
def fmt_time(v):
    if v is None:
        return ""
    if isinstance(v, timedelta):
        s = int(v.total_seconds())
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}"
    if isinstance(v, time):
        return v.strftime("%H:%M")
    return str(v)[:5]

@app.template_filter("d")
def fmt_date(v):
    if v is None:
        return ""
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return str(v)[:10]

@app.template_filter("dt")
def fmt_datetime(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v)[:16] if v else ""

def options():
    return {
        "conferences": rows("SELECT conference_id, acronym, name, start_date, end_date FROM conference ORDER BY conference_id"),
        "tracks": rows("SELECT t.track_id, t.name, c.acronym FROM track t "
                       "JOIN conference c ON c.conference_id = t.conference_id ORDER BY t.track_id"),
        "sessions": rows("SELECT s.session_id, s.title, s.session_date, c.acronym FROM conference_session s "
                         "JOIN conference c ON c.conference_id = s.conference_id ORDER BY s.session_id"),
        "authors": rows("SELECT u.user_id, u.given_name, u.surname, u.email FROM author a "
                        "JOIN app_user u ON u.user_id = a.author_id ORDER BY u.surname, u.given_name"),
        "reviewers": rows("SELECT u.user_id, u.given_name, u.surname, u.email FROM reviewer r "
                          "JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY u.surname, u.given_name"),
        "papers": rows("SELECT paper_id, title, status FROM paper ORDER BY paper_id"),
        "statuses": STATUSES,
        "recommendations": RECOMMENDATIONS,
    }

def check_not_self_review(conn, paper_id, reviewer_id):
    if value(conn, "SELECT COUNT(*) FROM paper_author WHERE paper_id = :p AND author_id = :r",
             p=paper_id, r=reviewer_id):
        raise AppError("Self-review rejected: this reviewer is an author of the selected paper.")

def check_session_assignment(conn, status, track_id, session_id):
    if session_id is None:
        return
    if status != "accepted":
        raise AppError("Invalid session assignment: only accepted papers can be assigned to a session. Set the status to 'accepted' or choose 'not scheduled'.")
    track_conf = value(conn, "SELECT conference_id FROM track WHERE track_id = :t", t=track_id)
    session_conf = value(conn, "SELECT conference_id FROM conference_session WHERE session_id = :s", s=session_id)
    if session_conf is None:
        raise AppError("The selected session does not exist.")
    if track_conf != session_conf:
        raise AppError("Invalid session assignment: the session belongs to a different conference than the paper's track.")

@app.route("/")
def index():
    counts = one("""
        SELECT (SELECT COUNT(*) FROM app_user) AS users, (SELECT COUNT(*) FROM paper) AS papers,
               (SELECT COUNT(*) FROM review) AS reviews, (SELECT COUNT(*) FROM conference_session) AS sessions,
               (SELECT COUNT(*) FROM conference) AS conferences, (SELECT COUNT(*) FROM track) AS tracks
    """)
    conferences = rows("SELECT conference_id, acronym, name, city, country, start_date, end_date, "
                       "submission_deadline, review_deadline FROM conference ORDER BY conference_id")
    return render_template("index.html", counts=counts, conferences=conferences)

@app.route("/users")
def users():
    data = rows("""
        SELECT u.user_id, u.given_name, u.surname, u.email, u.affiliation, u.country,
               a.author_id IS NOT NULL AS is_author, r.reviewer_id IS NOT NULL AS is_reviewer
        FROM app_user u
        LEFT JOIN author a   ON a.author_id = u.user_id
        LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
        ORDER BY u.user_id
    """)
    return render_template("users.html", users=data)

def load_user(user_id):
    u = one("SELECT * FROM app_user WHERE user_id = :id", id=user_id)
    if not u:
        abort(404)
    a = one("SELECT orcid FROM author WHERE author_id = :id", id=user_id)
    r = one("SELECT years_experience FROM reviewer WHERE reviewer_id = :id", id=user_id)
    u["is_author"] = a is not None
    u["orcid"] = (a or {}).get("orcid") or ""
    u["areas"] = ", ".join(x["area_label"] for x in rows(
        "SELECT area_label FROM author_research_area WHERE author_id = :id ORDER BY area_label", id=user_id))
    u["is_reviewer"] = r is not None
    u["years_experience"] = "" if r is None else r["years_experience"]
    u["expertise"] = ", ".join(x["area_label"] for x in rows(
        "SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :id ORDER BY area_label", id=user_id))
    u["pools"] = [x["conference_id"] for x in rows(
        "SELECT conference_id FROM conference_reviewer WHERE reviewer_id = :id", id=user_id)]
    return u

def form_user():
    d = {k: request.form.get(k, "") for k in
         ("given_name", "surname", "email", "affiliation", "country", "phone_number",
          "orcid", "areas", "years_experience", "expertise")}
    d["is_author"] = "is_author" in request.form
    d["is_reviewer"] = "is_reviewer" in request.form
    d["pools"] = [int(x) for x in request.form.getlist("pools")]
    return d

def save_user(conn, user_id):
    p = {k: required(k, label) for k, label in [
        ("given_name", "Given name"), ("surname", "Surname"), ("email", "Email"),
        ("affiliation", "Affiliation"), ("country", "Country"), ("phone_number", "Phone number")]}
    is_author = "is_author" in request.form
    is_reviewer = "is_reviewer" in request.form
    if not (is_author or is_reviewer):
        raise AppError("Every user must have the author role, the reviewer role, or both.")

    if user_id is None:
        user_id = run(conn, """INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
                               VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)""",
                      **p).lastrowid
    else:
        run(conn, """UPDATE app_user SET given_name = :given_name, surname = :surname, email = :email,
                     affiliation = :affiliation, country = :country, phone_number = :phone_number
                     WHERE user_id = :id""", id=user_id, **p)

    has_author = value(conn, "SELECT COUNT(*) FROM author WHERE author_id = :id", id=user_id)
    if is_author:
        areas = label_list("areas")
        if not areas:
            raise AppError("An author needs at least one research area.")
        orcid = field("orcid") or None
        if has_author:
            run(conn, "UPDATE author SET orcid = :o WHERE author_id = :id", o=orcid, id=user_id)
        else:
            run(conn, "INSERT INTO author (author_id, orcid) VALUES (:id, :o)", o=orcid, id=user_id)
        run(conn, "DELETE FROM author_research_area WHERE author_id = :id", id=user_id)
        for a in areas:
            run(conn, "INSERT INTO author_research_area (author_id, area_label) VALUES (:id, :a)", id=user_id, a=a)
    elif has_author:
        run(conn, "DELETE FROM author WHERE author_id = :id", id=user_id)

    has_reviewer = value(conn, "SELECT COUNT(*) FROM reviewer WHERE reviewer_id = :id", id=user_id)
    if is_reviewer:
        years = integer("years_experience", "Years of reviewing experience")
        expertise = label_list("expertise")
        if not expertise:
            raise AppError("A reviewer needs at least one expertise area.")
        if has_reviewer:
            run(conn, "UPDATE reviewer SET years_experience = :y WHERE reviewer_id = :id", y=years, id=user_id)
        else:
            run(conn, "INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)", y=years, id=user_id)
        run(conn, "DELETE FROM reviewer_expertise WHERE reviewer_id = :id", id=user_id)
        for e in expertise:
            run(conn, "INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES (:id, :e)", id=user_id, e=e)
        wanted = {int(x) for x in request.form.getlist("pools")}
        current = {r[0] for r in run(conn, "SELECT conference_id FROM conference_reviewer WHERE reviewer_id = :id",
                                     id=user_id).fetchall()}
        for c in current - wanted:
            run(conn, "DELETE FROM conference_reviewer WHERE conference_id = :c AND reviewer_id = :id", c=c, id=user_id)
        for c in wanted - current:
            run(conn, "INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES (:c, :id)", c=c, id=user_id)
    elif has_reviewer:
        run(conn, "DELETE FROM reviewer WHERE reviewer_id = :id", id=user_id)
    return user_id

@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_user(conn, None), "User created.")
        if ok:
            return redirect(url_for("users"))
        return render_template("user_form.html", u=form_user(), new=True, **options())
    blank = {"is_author": True, "is_reviewer": False, "pools": []}
    return render_template("user_form.html", u=blank, new=True, **options())

@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_user(conn, user_id), "User updated.")
        if ok:
            return redirect(url_for("users"))
        u = form_user()
        u["user_id"] = user_id
        return render_template("user_form.html", u=u, new=False, **options())
    return render_template("user_form.html", u=load_user(user_id), new=False, **options())

@app.route("/users/<int:user_id>/delete", methods=["POST"])
def user_delete(user_id):
    attempt(lambda conn: run(conn, "DELETE FROM app_user WHERE user_id = :id", id=user_id), "User deleted.")
    return redirect(url_for("users"))

@app.route("/papers")
def papers():
    data = rows("""
        SELECT p.paper_id, p.title, p.status, t.name AS track_name, c.acronym,
               s.title AS session_title, u.given_name, u.surname
        FROM paper p
        JOIN track t       ON t.track_id = p.track_id
        JOIN conference c  ON c.conference_id = t.conference_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding = TRUE
        LEFT JOIN app_user u      ON u.user_id = pa.author_id
        ORDER BY p.paper_id
    """)
    return render_template("papers.html", papers=data)

def paper_fields(conn):
    p = {
        "track_id": integer("track_id", "Track"),
        "title": required("title", "Title"),
        "abstract": required("abstract", "Abstract"),
        "submission_date": required("submission_date", "Submission date"),
        "status": required("status", "Status"),
        "session_id": integer("session_id", "Session", optional=True),
    }
    if p["status"] not in STATUSES:
        raise AppError("Invalid paper status.")
    check_session_assignment(conn, p["status"], p["track_id"], p["session_id"])
    return p


def create_paper(conn):
    p = paper_fields(conn)
    keywords = label_list("keywords")
    if not keywords:
        raise AppError("A paper needs at least one keyword.")
    author_id = integer("author_id", "Corresponding author")
    file_location = required("file_location", "File location of version 1")
    paper_id = run(conn, """INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
                            VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)""",
                   **p).lastrowid
    for k in keywords:
        run(conn, "INSERT INTO paper_keyword (paper_id, keyword) VALUES (:p, :k)", p=paper_id, k=k)
    run(conn, """INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                 VALUES (:p, :a, 1, TRUE)""", p=paper_id, a=author_id)
    run(conn, """INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                 VALUES (:p, 1, :f, :t, NULL)""", p=paper_id, f=file_location,
        t=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return paper_id

@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "POST":
        ok, paper_id = attempt(create_paper, "Paper created with its author, keywords and first version.")
        if ok:
            return redirect(url_for("paper_detail", paper_id=paper_id))
        return render_template("paper_form.html", p=request.form, new=True, **options())
    blank = {"status": "submitted", "submission_date": date.today().isoformat()}
    return render_template("paper_form.html", p=blank, new=True, **options())

@app.route("/papers/<int:paper_id>")
def paper_detail(paper_id):
    p = one("""SELECT p.*, t.name AS track_name, c.acronym, s.title AS session_title
               FROM paper p JOIN track t ON t.track_id = p.track_id
               JOIN conference c ON c.conference_id = t.conference_id
               LEFT JOIN conference_session s ON s.session_id = p.session_id
               WHERE p.paper_id = :id""", id=paper_id)
    if not p:
        abort(404)
    authors = rows("""SELECT pa.author_id, pa.author_position, pa.is_corresponding, u.given_name, u.surname, u.email
                      FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                      WHERE pa.paper_id = :id ORDER BY pa.author_position""", id=paper_id)
    keywords = rows("SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword", id=paper_id)
    versions = rows("SELECT * FROM paper_version WHERE paper_id = :id ORDER BY version_no DESC", id=paper_id)
    reviews = rows("""SELECT r.review_id, r.overall_score, r.recommendation, r.review_submission_date,
                             u.given_name, u.surname
                      FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
                      WHERE r.paper_id = :id ORDER BY r.review_id""", id=paper_id)
    next_position = max([a["author_position"] for a in authors], default=0) + 1
    next_version = max([v["version_no"] for v in versions], default=0) + 1
    return render_template("paper_detail.html", p=p, paper_authors=authors, keywords=keywords, versions=versions,
                           reviews=reviews, next_position=next_position, next_version=next_version,
                           now=datetime.now().strftime("%Y-%m-%dT%H:%M"), **options())

@app.route("/papers/<int:paper_id>/edit", methods=["GET", "POST"])
def paper_edit(paper_id):
    if request.method == "POST":
        def update(conn):
            p = paper_fields(conn)
            run(conn, """UPDATE paper SET track_id = :track_id, title = :title, abstract = :abstract,
                         submission_date = :submission_date, status = :status, session_id = :session_id
                         WHERE paper_id = :id""", id=paper_id, **p)
        ok, _ = attempt(update, "Paper updated.")
        if ok:
            return redirect(url_for("paper_detail", paper_id=paper_id))
        p = dict(request.form)
        p["paper_id"] = paper_id
        return render_template("paper_form.html", p=p, new=False, **options())
    p = one("SELECT * FROM paper WHERE paper_id = :id", id=paper_id)
    if not p:
        abort(404)
    p["submission_date"] = fmt_date(p["submission_date"])
    return render_template("paper_form.html", p=p, new=False, **options())

@app.route("/papers/<int:paper_id>/delete", methods=["POST"])
def paper_delete(paper_id):
    attempt(lambda conn: run(conn, "DELETE FROM paper WHERE paper_id = :id", id=paper_id),
            "Paper deleted together with its authorship, keywords, versions and reviews.")
    return redirect(url_for("papers"))

@app.route("/papers/<int:paper_id>/authors/add", methods=["POST"])
def author_add(paper_id):
    def add(conn):
        author_id = integer("author_id", "Author")
        position = integer("author_position", "Author position")
        corresponding = "is_corresponding" in request.form
        if value(conn, "SELECT COUNT(*) FROM review WHERE paper_id = :p AND reviewer_id = :a",
                 p=paper_id, a=author_id):
            raise AppError("Self-review conflict: this person has already reviewed this paper, "
                           "so they cannot be added as its author.")
        if corresponding:
            run(conn, "UPDATE paper_author SET is_corresponding = FALSE WHERE paper_id = :p", p=paper_id)
        run(conn, """INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                     VALUES (:p, :a, :pos, :c)""", p=paper_id, a=author_id, pos=position, c=corresponding)
    attempt(add, "Author added.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/authors/<int:author_id>/corresponding", methods=["POST"])
def author_corresponding(paper_id, author_id):
    def change(conn):
        run(conn, "UPDATE paper_author SET is_corresponding = FALSE WHERE paper_id = :p", p=paper_id)
        run(conn, "UPDATE paper_author SET is_corresponding = TRUE WHERE paper_id = :p AND author_id = :a",
            p=paper_id, a=author_id)
    attempt(change, "Corresponding author changed.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/authors/<int:author_id>/remove", methods=["POST"])
def author_remove(paper_id, author_id):
    def remove(conn):
        if value(conn, "SELECT COUNT(*) FROM paper_author WHERE paper_id = :p", p=paper_id) <= 1:
            raise AppError("A paper must have at least one author.")
        if value(conn, "SELECT is_corresponding FROM paper_author WHERE paper_id = :p AND author_id = :a",
                 p=paper_id, a=author_id):
            raise AppError("This is the corresponding author. Make another author corresponding first.")
        run(conn, "DELETE FROM paper_author WHERE paper_id = :p AND author_id = :a", p=paper_id, a=author_id)
    attempt(remove, "Author removed.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/keywords/add", methods=["POST"])
def keyword_add(paper_id):
    def add(conn):
        words = label_list("keyword")
        if not words:
            raise AppError("Enter a keyword.")
        for k in words:
            run(conn, "INSERT INTO paper_keyword (paper_id, keyword) VALUES (:p, :k)", p=paper_id, k=k)
    attempt(add, "Keyword added.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/keywords/remove", methods=["POST"])
def keyword_remove(paper_id):
    def remove(conn):
        if value(conn, "SELECT COUNT(*) FROM paper_keyword WHERE paper_id = :p", p=paper_id) <= 1:
            raise AppError("A paper must keep at least one keyword.")
        run(conn, "DELETE FROM paper_keyword WHERE paper_id = :p AND keyword = :k", p=paper_id, k=field("keyword"))
    attempt(remove, "Keyword removed.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/versions/add", methods=["POST"])
def version_add(paper_id):
    def add(conn):
        run(conn, """INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                     VALUES (:p, :v, :f, :t, :n)""",
            p=paper_id, v=integer("version_no", "Version number"), f=required("file_location", "File location"),
            t=required("uploaded_at", "Upload date and time").replace("T", " "), n=field("change_note") or None)
    attempt(add, "Version added.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/papers/<int:paper_id>/versions/<int:version_no>/delete", methods=["POST"])
def version_delete(paper_id, version_no):
    def remove(conn):
        if value(conn, "SELECT COUNT(*) FROM paper_version WHERE paper_id = :p", p=paper_id) <= 1:
            raise AppError("A paper must keep at least one version.")
        run(conn, "DELETE FROM paper_version WHERE paper_id = :p AND version_no = :v", p=paper_id, v=version_no)
    attempt(remove, "Version deleted.")
    return redirect(url_for("paper_detail", paper_id=paper_id))

@app.route("/reviews")
def reviews():
    data = rows("""
        SELECT r.review_id, r.paper_id, p.title, u.given_name, u.surname,
               r.overall_score, r.recommendation, r.review_submission_date
        FROM review r
        JOIN paper p    ON p.paper_id = r.paper_id
        JOIN app_user u ON u.user_id = r.reviewer_id
        ORDER BY r.review_id
    """)
    return render_template("reviews.html", reviews=data)

def save_review(conn, review_id):
    p = {
        "paper_id": integer("paper_id", "Paper"),
        "reviewer_id": integer("reviewer_id", "Reviewer"),
        "overall_score": integer("overall_score", "Overall score"),
        "recommendation": required("recommendation", "Recommendation"),
        "comments_for_authors": required("comments_for_authors", "Comments for authors"),
        "confidential_comments": field("confidential_comments") or None,
        "review_submission_date": required("review_submission_date", "Review date"),
    }
    check_not_self_review(conn, p["paper_id"], p["reviewer_id"])
    if not value(conn, """SELECT COUNT(*) FROM paper pp JOIN track t ON t.track_id = pp.track_id
                          JOIN conference_reviewer cr ON cr.conference_id = t.conference_id
                          WHERE pp.paper_id = :p AND cr.reviewer_id = :r""",
                 p=p["paper_id"], r=p["reviewer_id"]):
        raise AppError("This reviewer is not in the reviewer pool of the paper's conference.")
    if review_id is None:
        run(conn, """INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation, comments_for_authors,
                                         confidential_comments, review_submission_date)
                     VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation, :comments_for_authors,
                             :confidential_comments, :review_submission_date)""", **p)
    else:
        run(conn, """UPDATE review SET paper_id = :paper_id, reviewer_id = :reviewer_id,
                     overall_score = :overall_score, recommendation = :recommendation,
                     comments_for_authors = :comments_for_authors, confidential_comments = :confidential_comments,
                     review_submission_date = :review_submission_date
                     WHERE review_id = :id""", id=review_id, **p)

@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_review(conn, None), "Review saved.")
        if ok:
            return redirect(url_for("reviews"))
        return render_template("review_form.html", r=request.form, new=True, **options())
    blank = {"review_submission_date": date.today().isoformat(), "paper_id": request.args.get("paper_id", "")}
    return render_template("review_form.html", r=blank, new=True, **options())

@app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
def review_edit(review_id):
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_review(conn, review_id), "Review updated.")
        if ok:
            return redirect(url_for("reviews"))
        r = dict(request.form)
        r["review_id"] = review_id
        return render_template("review_form.html", r=r, new=False, **options())
    r = one("SELECT * FROM review WHERE review_id = :id", id=review_id)
    if not r:
        abort(404)
    r["review_submission_date"] = fmt_date(r["review_submission_date"])
    return render_template("review_form.html", r=r, new=False, **options())

@app.route("/reviews/<int:review_id>/delete", methods=["POST"])
def review_delete(review_id):
    attempt(lambda conn: run(conn, "DELETE FROM review WHERE review_id = :id", id=review_id), "Review deleted.")
    return redirect(url_for("reviews"))

@app.route("/sessions")
def sessions():
    data = rows("""
        SELECT s.session_id, s.title, s.session_date, s.start_time, s.end_time, s.room_label,
               c.acronym, u.given_name, u.surname,
               (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS paper_count
        FROM conference_session s
        JOIN conference c ON c.conference_id = s.conference_id
        JOIN app_user u   ON u.user_id = s.chair_id
        ORDER BY s.session_id
    """)
    return render_template("sessions.html", sessions=data)

def save_session(conn, session_id):
    p = {
        "conference_id": integer("conference_id", "Conference"),
        "title": required("title", "Title"),
        "session_date": required("session_date", "Session date"),
        "start_time": required("start_time", "Start time"),
        "end_time": required("end_time", "End time"),
        "room_label": required("room_label", "Room"),
        "chair_id": integer("chair_id", "Chair"),
    }
    conf = run(conn, "SELECT start_date, end_date FROM conference WHERE conference_id = :c",
               c=p["conference_id"]).mappings().first()
    if conf and not (fmt_date(conf["start_date"]) <= p["session_date"] <= fmt_date(conf["end_date"])):
        raise AppError(f"The session date must be within the conference dates "
                       f"({fmt_date(conf['start_date'])} to {fmt_date(conf['end_date'])}).")
    if session_id is None:
        run(conn, """INSERT INTO conference_session (conference_id, title, session_date, start_time, end_time,
                                                     room_label, chair_id)
                     VALUES (:conference_id, :title, :session_date, :start_time, :end_time, :room_label, :chair_id)""",
            **p)
    else:
        bad = value(conn, """SELECT COUNT(*) FROM paper pp JOIN track t ON t.track_id = pp.track_id
                             WHERE pp.session_id = :s AND t.conference_id <> :c""",
                    s=session_id, c=p["conference_id"])
        if bad:
            raise AppError(f"Invalid session assignment: {bad} paper(s) in this session belong to another conference. Unassign them before moving the session.")
        run(conn, """UPDATE conference_session SET conference_id = :conference_id, title = :title,
                     session_date = :session_date, start_time = :start_time, end_time = :end_time,
                     room_label = :room_label, chair_id = :chair_id
                     WHERE session_id = :id""", id=session_id, **p)

@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_session(conn, None), "Session created.")
        if ok:
            return redirect(url_for("sessions"))
        return render_template("session_form.html", s=request.form, new=True, **options())
    return render_template("session_form.html", s={}, new=True, **options())

@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def session_edit(session_id):
    if request.method == "POST":
        ok, _ = attempt(lambda conn: save_session(conn, session_id), "Session updated.")
        if ok:
            return redirect(url_for("sessions"))
        s = dict(request.form)
        s["session_id"] = session_id
        return render_template("session_form.html", s=s, new=False, **options())
    s = one("SELECT * FROM conference_session WHERE session_id = :id", id=session_id)
    if not s:
        abort(404)
    s["session_date"] = fmt_date(s["session_date"])
    s["start_time"] = fmt_time(s["start_time"])
    s["end_time"] = fmt_time(s["end_time"])
    papers_in = rows("SELECT paper_id, title FROM paper WHERE session_id = :id ORDER BY paper_id", id=session_id)
    return render_template("session_form.html", s=s, new=False, papers_in=papers_in, **options())

@app.route("/sessions/<int:session_id>/delete", methods=["POST"])
def session_delete(session_id):
    def remove(conn):
        n = value(conn, "SELECT COUNT(*) FROM paper WHERE session_id = :id", id=session_id)
        run(conn, "DELETE FROM conference_session WHERE session_id = :id", id=session_id)
        return n
    ok, n = attempt(remove, "Session deleted.")
    if ok and n:
        flash(f"{n} paper(s) in that session are now unscheduled.", "success")
    return redirect(url_for("sessions"))

@app.route("/schedule")
def schedule():
    try:
        data = rows("SELECT * FROM accepted_paper_schedule "
                    "ORDER BY conference_id, session_date, start_time, session_id, paper_id")
    except DBAPIError:
        data = None
    return render_template("schedule.html", rows=data)

@app.errorhandler(404)
def not_found(_):
    return render_template("message.html", title="Not found", text="That record does not exist."), 404

if __name__ == "__main__":
    app.run(debug=True)