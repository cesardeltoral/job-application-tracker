"""Server-side validation for every form.

Each ``validate_*`` function takes the submitted form (a dict-like object)
and returns ``(data, errors)``:
  * data   - cleaned values ready to hand to database.py
  * errors - {field_name: message}; empty when the input is valid
"""

import re
from datetime import date

from database import JOB_TYPES, STATUSES
from matching import parse_skills

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,20}$")
URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)


def _text(form, name, errors, label, max_len, required=False):
    value = (form.get(name) or "").strip()
    if required and not value:
        errors[name] = f"{label} is required."
    elif len(value) > max_len:
        errors[name] = f"{label} must be {max_len} characters or fewer."
    return value or None


def _url(form, name, errors, label, max_len):
    value = _text(form, name, errors, label, max_len)
    if value and name not in errors and not URL_RE.match(value):
        errors[name] = f"{label} must start with http:// or https://"
    return value


def _int(form, name, errors, label, minimum=None, maximum=None, required=False):
    raw = (form.get(name) or "").strip().replace(",", "")
    if not raw:
        if required:
            errors[name] = f"{label} is required."
        return None
    try:
        value = int(raw)
    except ValueError:
        errors[name] = f"{label} must be a whole number."
        return None
    if minimum is not None and value < minimum:
        errors[name] = f"{label} must be at least {minimum}."
    elif maximum is not None and value > maximum:
        errors[name] = f"{label} must be at most {maximum}."
    return value


def _date(form, name, errors, label, required=False, allow_future=True):
    raw = (form.get(name) or "").strip()
    if not raw:
        if required:
            errors[name] = f"{label} is required."
        return None
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        errors[name] = f"{label} must be a valid date (YYYY-MM-DD)."
        return None
    if not allow_future and value > date.today():
        errors[name] = f"{label} cannot be in the future."
    return value


def _choice(form, name, errors, label, choices, default=None):
    value = (form.get(name) or "").strip() or default
    if value not in choices:
        errors[name] = f"Please choose a valid {label.lower()}."
    return value


def _checkbox(form, name):
    return (form.get(name) or "").lower() in ("on", "true", "1", "yes")


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
def validate_company(form):
    errors = {}
    data = {
        "company_name": _text(form, "company_name", errors, "Company name", 100, required=True),
        "industry": _text(form, "industry", errors, "Industry", 50),
        "website": _url(form, "website", errors, "Website", 200),
        "city": _text(form, "city", errors, "City", 50),
        "state": _text(form, "state", errors, "State", 50),
        "notes": _text(form, "notes", errors, "Notes", 5000),
    }
    return data, errors


def validate_job(form, valid_company_ids):
    errors = {}
    company_id = _int(form, "company_id", errors, "Company", required=True)
    if company_id is not None and company_id not in valid_company_ids:
        errors["company_id"] = "Please choose a company from the list."

    salary_min = _int(form, "salary_min", errors, "Minimum salary", minimum=0, maximum=10_000_000)
    salary_max = _int(form, "salary_max", errors, "Maximum salary", minimum=0, maximum=10_000_000)
    if (salary_min is not None and salary_max is not None
            and salary_min > salary_max and "salary_max" not in errors):
        errors["salary_max"] = "Maximum salary must be greater than or equal to the minimum."

    requirements = {}
    required_skills = parse_skills(form.get("required_skills"))
    preferred_skills = parse_skills(form.get("preferred_skills"))
    education = _text(form, "education", errors, "Education", 100)
    experience = _int(form, "experience_years", errors, "Years of experience", minimum=0, maximum=50)
    if required_skills:
        requirements["required_skills"] = required_skills
    if preferred_skills:
        requirements["preferred_skills"] = preferred_skills
    if education:
        requirements["education"] = education
    if experience is not None:
        requirements["experience_years"] = experience
    requirements["remote_option"] = _checkbox(form, "remote_option")

    data = {
        "company_id": company_id,
        "job_title": _text(form, "job_title", errors, "Job title", 100, required=True),
        "job_type": _choice(form, "job_type", errors, "Job type", JOB_TYPES, default="Full-time"),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "job_url": _url(form, "job_url", errors, "Job URL", 300),
        "date_posted": _date(form, "date_posted", errors, "Date posted"),
        "requirements": requirements,
    }
    return data, errors


def validate_application(form, valid_job_ids):
    errors = {}
    job_id = _int(form, "job_id", errors, "Job", required=True)
    if job_id is not None and job_id not in valid_job_ids:
        errors["job_id"] = "Please choose a job from the list."

    interview = {}
    rounds = _int(form, "interview_rounds", errors, "Interview rounds", minimum=0, maximum=20)
    rating = _int(form, "rating", errors, "Rating", minimum=1, maximum=5)
    interviewers = parse_skills(form.get("interviewers"))  # same comma splitting rules
    questions = _lines(form.get("technical_questions"))
    feedback = _text(form, "feedback", errors, "Feedback", 2000)
    next_steps = _text(form, "next_steps", errors, "Next steps", 300)
    for key, value in (("interview_rounds", rounds), ("interviewers", interviewers),
                       ("technical_questions", questions), ("feedback", feedback),
                       ("next_steps", next_steps), ("rating", rating)):
        if value not in (None, [], ""):
            interview[key] = value

    data = {
        "job_id": job_id,
        "application_date": _date(form, "application_date", errors, "Application date",
                                  required=True, allow_future=False),
        "status": _choice(form, "status", errors, "Status", STATUSES, default="Applied"),
        "resume_version": _text(form, "resume_version", errors, "Resume version", 50),
        "cover_letter_sent": _checkbox(form, "cover_letter_sent"),
        "interview_data": interview,
    }
    return data, errors


def validate_contact(form, valid_company_ids):
    errors = {}
    company_id = _int(form, "company_id", errors, "Company", required=True)
    if company_id is not None and company_id not in valid_company_ids:
        errors["company_id"] = "Please choose a company from the list."

    email = _text(form, "email", errors, "Email", 100)
    if email and "email" not in errors and not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."
    phone = _text(form, "phone", errors, "Phone", 20)
    if phone and "phone" not in errors and not PHONE_RE.match(phone):
        errors["phone"] = "Phone may only contain digits, spaces and + ( ) - ."

    data = {
        "company_id": company_id,
        "contact_name": _text(form, "contact_name", errors, "Contact name", 100, required=True),
        "title": _text(form, "title", errors, "Title", 100),
        "email": email,
        "phone": phone,
        "linkedin_url": _url(form, "linkedin_url", errors, "LinkedIn URL", 200),
        "notes": _text(form, "notes", errors, "Notes", 5000),
    }
    return data, errors
