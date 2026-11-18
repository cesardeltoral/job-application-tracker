"""Database access layer for the Job Application Tracker.

Every query uses parameterized placeholders (%s) so user input is never
concatenated into SQL. Each helper opens a connection, does its work and
closes the connection in a ``finally`` block.
"""

import json
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def get_db():
    """Open a new MySQL connection using settings from .env."""
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), one=False):
    """Run a SELECT and return a list of dict rows (or a single row if one=True)."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE inside a transaction.

    Returns the new row id for INSERTs, otherwise the affected row count.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        result = cursor.lastrowid or cursor.rowcount
        cursor.close()
        return result
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def load_json(value):
    """Turn a JSON column value (str/bytes/None) into a Python object."""
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def dump_json(value):
    """Serialize a dict for a JSON column; empty dicts are stored as NULL."""
    return json.dumps(value) if value else None


def _decode(rows, column):
    for row in rows:
        row[column] = load_json(row.get(column)) or {}
    return rows


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
def get_companies(search=""):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)     AS job_count,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = ()
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s"
        like = f"%{search}%"
        params = (like, like, like)
    sql += " ORDER BY c.company_name"
    return query(sql, params)


def get_company(company_id):
    return query("SELECT * FROM companies WHERE company_id = %s", (company_id,), one=True)


def company_name_taken(name, exclude_id=None):
    row = query(
        "SELECT company_id FROM companies WHERE company_name = %s AND company_id <> %s",
        (name, exclude_id or 0),
        one=True,
    )
    return row is not None


def create_company(data):
    return execute(
        """INSERT INTO companies (company_name, industry, website, city, state, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"]),
    )


def update_company(company_id, data):
    return execute(
        """UPDATE companies
           SET company_name = %s, industry = %s, website = %s, city = %s, state = %s, notes = %s
           WHERE company_id = %s""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"], company_id),
    )


def delete_company(company_id):
    return execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def company_choices():
    """(id, name) pairs for <select> dropdowns."""
    return query("SELECT company_id, company_name FROM companies ORDER BY company_name")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
JOB_SELECT = """
    SELECT j.*, c.company_name,
           (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
    FROM jobs j
    JOIN companies c ON c.company_id = j.company_id
"""


def get_jobs(search="", job_type="", company_id=None):
    clauses, params = [], []
    if search:
        clauses.append("(j.job_title LIKE %s OR c.company_name LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if job_type:
        clauses.append("j.job_type = %s")
        params.append(job_type)
    if company_id:
        clauses.append("j.company_id = %s")
        params.append(company_id)
    sql = JOB_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    return _decode(query(sql, tuple(params)), "requirements")


def get_job(job_id):
    row = query(JOB_SELECT + " WHERE j.job_id = %s", (job_id,), one=True)
    if row:
        row["requirements"] = load_json(row["requirements"]) or {}
    return row


def _job_params(data):
    return (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
            data["salary_max"], data["job_url"], data["date_posted"],
            dump_json(data["requirements"]))


def create_job(data):
    return execute(
        """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                             job_url, date_posted, requirements)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        _job_params(data),
    )


def update_job(job_id, data):
    return execute(
        """UPDATE jobs
           SET company_id = %s, job_title = %s, job_type = %s, salary_min = %s, salary_max = %s,
               job_url = %s, date_posted = %s, requirements = %s
           WHERE job_id = %s""",
        _job_params(data) + (job_id,),
    )


def delete_job(job_id):
    return execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


def job_choices():
    return query(
        """SELECT j.job_id, j.job_title, c.company_name
           FROM jobs j JOIN companies c ON c.company_id = j.company_id
           ORDER BY c.company_name, j.job_title"""
    )


# ---------------------------------------------------------------------------
# Applications (read through the application_overview view)
# ---------------------------------------------------------------------------
def get_applications(status="", search="", job_id=None, company_id=None):
    clauses, params = [], []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if search:
        clauses.append("(job_title LIKE %s OR company_name LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if job_id:
        clauses.append("job_id = %s")
        params.append(job_id)
    if company_id:
        clauses.append("company_id = %s")
        params.append(company_id)
    sql = "SELECT * FROM application_overview"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY application_date DESC, application_id DESC"
    return _decode(query(sql, tuple(params)), "interview_data")


def get_application(application_id):
    row = query(
        "SELECT * FROM application_overview WHERE application_id = %s",
        (application_id,),
        one=True,
    )
    if row:
        row["interview_data"] = load_json(row["interview_data"]) or {}
    return row


def _application_params(data):
    return (data["job_id"], data["application_date"], data["status"], data["resume_version"],
            data["cover_letter_sent"], dump_json(data["interview_data"]))


def create_application(data):
    return execute(
        """INSERT INTO applications (job_id, application_date, status, resume_version,
                                     cover_letter_sent, interview_data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        _application_params(data),
    )


def update_application(application_id, data):
    return execute(
        """UPDATE applications
           SET job_id = %s, application_date = %s, status = %s, resume_version = %s,
               cover_letter_sent = %s, interview_data = %s
           WHERE application_id = %s""",
        _application_params(data) + (application_id,),
    )


def delete_application(application_id):
    return execute("DELETE FROM applications WHERE application_id = %s", (application_id,))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
CONTACT_SELECT = """
    SELECT k.*, c.company_name
    FROM contacts k
    JOIN companies c ON c.company_id = k.company_id
"""


def get_contacts(search="", company_id=None):
    clauses, params = [], []
    if search:
        clauses.append("(k.contact_name LIKE %s OR k.title LIKE %s OR c.company_name LIKE %s)")
        params += [f"%{search}%"] * 3
    if company_id:
        clauses.append("k.company_id = %s")
        params.append(company_id)
    sql = CONTACT_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY k.contact_name"
    return query(sql, tuple(params))


def get_contact(contact_id):
    return query(CONTACT_SELECT + " WHERE k.contact_id = %s", (contact_id,), one=True)


def _contact_params(data):
    return (data["company_id"], data["contact_name"], data["title"], data["email"],
            data["phone"], data["linkedin_url"], data["notes"])


def create_contact(data):
    return execute(
        """INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        _contact_params(data),
    )


def update_contact(contact_id, data):
    return execute(
        """UPDATE contacts
           SET company_id = %s, contact_name = %s, title = %s, email = %s, phone = %s,
               linkedin_url = %s, notes = %s
           WHERE contact_id = %s""",
        _contact_params(data) + (contact_id,),
    )


def delete_contact(contact_id):
    return execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# ---------------------------------------------------------------------------
# Dashboard statistics
# ---------------------------------------------------------------------------
def get_dashboard_stats():
    counts = query(
        """SELECT (SELECT COUNT(*) FROM companies)    AS companies,
                  (SELECT COUNT(*) FROM jobs)         AS jobs,
                  (SELECT COUNT(*) FROM applications) AS applications,
                  (SELECT COUNT(*) FROM contacts)     AS contacts""",
        one=True,
    )

    status_rows = query(
        "SELECT status, COUNT(*) AS total FROM applications GROUP BY status"
    )
    by_status = {status: 0 for status in STATUSES}
    for row in status_rows:
        by_status[row["status"]] = row["total"]

    total = counts["applications"]
    # "Responded" = anything that moved past the initial Applied stage, ignoring withdrawals.
    responded = sum(by_status[s] for s in ("Screening", "Interview", "Offer", "Rejected"))
    considered = total - by_status["Withdrawn"]
    response_rate = round(100 * responded / considered) if considered else 0

    # JSON_TABLE unpacks each job's required_skills array into rows.
    top_skills = query(
        """SELECT skills.skill, COUNT(*) AS total
           FROM jobs j,
                JSON_TABLE(j.requirements, '$.required_skills[*]'
                           COLUMNS (skill VARCHAR(100) PATH '$')) AS skills
           GROUP BY skills.skill
           ORDER BY total DESC, skills.skill
           LIMIT 8"""
    )

    recent = query(
        """SELECT application_id, application_date, status, job_title, company_name
           FROM application_overview
           ORDER BY application_date DESC, application_id DESC
           LIMIT 5"""
    )

    upcoming = query(
        """SELECT application_id, job_title, company_name, status,
                  interview_data->>'$.next_steps' AS next_steps
           FROM application_overview
           WHERE status IN ('Applied', 'Screening', 'Interview', 'Offer')
             AND interview_data->>'$.next_steps' IS NOT NULL
           ORDER BY application_date DESC"""
    )

    return {
        "counts": counts,
        "by_status": by_status,
        "response_rate": response_rate,
        "active": sum(by_status[s] for s in ("Applied", "Screening", "Interview")),
        "top_skills": top_skills,
        "recent": recent,
        "upcoming": upcoming,
    }


def get_jobs_for_matching():
    """All jobs with their decoded requirements, for the Job Match feature."""
    return get_jobs()
