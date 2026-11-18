"""Job Application Tracker - Flask application.

Run with:  python app.py   (then open http://127.0.0.1:5001)
"""

import os

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db
from matching import match_jobs, parse_skills
from validators import (validate_application, validate_company, validate_contact,
                        validate_job)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-secret")


@app.context_processor
def inject_constants():
    return {"JOB_TYPES": db.JOB_TYPES, "STATUSES": db.STATUSES}


@app.template_filter("money")
def money(value):
    return f"${value:,.0f}" if value is not None else "—"


@app.template_filter("choices")
def choices(items, value_key=None, text_key=None):
    """Turn a list into (value, text) pairs for the select() form macro."""
    if value_key is None:
        return [(item, item) for item in items]
    return [(item[value_key], item[text_key]) for item in items]


@app.template_filter("datefmt")
def datefmt(value):
    return value.strftime("%b %d, %Y") if value else "—"


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(mysql.connector.Error)
def database_error(error):
    app.logger.exception("Database error")
    return render_template("db_error.html", error=error), 500


def get_or_404(record):
    if record is None:
        abort(404)
    return record


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", stats=db.get_dashboard_stats())


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
@app.route("/companies")
def companies():
    search = request.args.get("q", "").strip()
    return render_template("companies.html", companies=db.get_companies(search), search=search)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404(db.get_company(company_id))
    return render_template(
        "company_detail.html",
        company=company,
        jobs=db.get_jobs(company_id=company_id),
        contacts=db.get_contacts(company_id=company_id),
        applications=db.get_applications(company_id=company_id),
    )


@app.route("/companies/new", methods=["GET", "POST"])
@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_form(company_id=None):
    company = get_or_404(db.get_company(company_id)) if company_id else {}
    errors = {}
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if not errors and db.company_name_taken(data["company_name"], company_id):
            errors["company_name"] = "A company with this name already exists."
        if not errors:
            if company_id:
                db.update_company(company_id, data)
                flash(f"Updated {data['company_name']}.", "success")
            else:
                company_id = db.create_company(data)
                flash(f"Added {data['company_name']}.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        company = {**company, **request.form}
    return render_template("company_form.html", company=company, errors=errors)


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = get_or_404(db.get_company(company_id))
    db.delete_company(company_id)
    flash(f"Deleted {company['company_name']} and its jobs, applications and contacts.", "success")
    return redirect(url_for("companies"))


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@app.route("/jobs")
def jobs():
    search = request.args.get("q", "").strip()
    job_type = request.args.get("type", "")
    return render_template("jobs.html", jobs=db.get_jobs(search, job_type),
                           search=search, job_type=job_type)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(db.get_job(job_id))
    return render_template("job_detail.html", job=job,
                           applications=db.get_applications(job_id=job_id))


def job_form_values(job):
    """Flatten the requirements JSON into the simple fields the form shows."""
    req = job.get("requirements") or {}
    return {
        **job,
        "required_skills": ", ".join(req.get("required_skills", [])),
        "preferred_skills": ", ".join(req.get("preferred_skills", [])),
        "education": req.get("education", ""),
        "experience_years": req.get("experience_years", ""),
        "remote_option": req.get("remote_option", False),
    }


@app.route("/jobs/new", methods=["GET", "POST"])
@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_form(job_id=None):
    job = job_form_values(get_or_404(db.get_job(job_id))) if job_id else {
        "company_id": request.args.get("company_id", type=int)}
    companies = db.company_choices()
    errors = {}
    if request.method == "POST":
        data, errors = validate_job(request.form, {c["company_id"] for c in companies})
        if not errors:
            if job_id:
                db.update_job(job_id, data)
                flash(f"Updated {data['job_title']}.", "success")
            else:
                job_id = db.create_job(data)
                flash(f"Added {data['job_title']}.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        job = {**request.form, "remote_option": "remote_option" in request.form,
               "company_id": request.form.get("company_id", type=int)}
    if not companies:
        flash("Add a company before adding jobs.", "info")
        return redirect(url_for("company_form"))
    return render_template("job_form.html", job=job, job_id=job_id,
                           companies=companies, errors=errors)


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = get_or_404(db.get_job(job_id))
    db.delete_job(job_id)
    flash(f"Deleted {job['job_title']} and its applications.", "success")
    return redirect(url_for("jobs"))


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    search = request.args.get("q", "").strip()
    return render_template("applications.html",
                           applications=db.get_applications(status, search),
                           status=status, search=search)


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = get_or_404(db.get_application(application_id))
    return render_template("application_detail.html", app_row=application)


def application_form_values(row):
    interview = row.get("interview_data") or {}
    return {
        **row,
        "interview_rounds": interview.get("interview_rounds", ""),
        "interviewers": ", ".join(interview.get("interviewers", [])),
        "technical_questions": "\n".join(interview.get("technical_questions", [])),
        "feedback": interview.get("feedback", ""),
        "next_steps": interview.get("next_steps", ""),
        "rating": interview.get("rating", ""),
    }


@app.route("/applications/new", methods=["GET", "POST"])
@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_form(application_id=None):
    if application_id:
        values = application_form_values(get_or_404(db.get_application(application_id)))
    else:
        values = {"job_id": request.args.get("job_id", type=int), "status": "Applied"}
    jobs = db.job_choices()
    errors = {}
    if request.method == "POST":
        data, errors = validate_application(request.form, {j["job_id"] for j in jobs})
        if not errors:
            if application_id:
                db.update_application(application_id, data)
                flash("Application updated.", "success")
            else:
                application_id = db.create_application(data)
                flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        values = {**request.form, "cover_letter_sent": "cover_letter_sent" in request.form,
                  "job_id": request.form.get("job_id", type=int)}
    if not jobs:
        flash("Add a job before logging an application.", "info")
        return redirect(url_for("job_form"))
    return render_template("application_form.html", values=values,
                           application_id=application_id, jobs=jobs, errors=errors)


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    get_or_404(db.get_application(application_id))
    db.delete_application(application_id)
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
@app.route("/contacts")
def contacts():
    search = request.args.get("q", "").strip()
    return render_template("contacts.html", contacts=db.get_contacts(search), search=search)


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    return render_template("contact_detail.html",
                           contact=get_or_404(db.get_contact(contact_id)))


@app.route("/contacts/new", methods=["GET", "POST"])
@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_form(contact_id=None):
    contact = get_or_404(db.get_contact(contact_id)) if contact_id else {
        "company_id": request.args.get("company_id", type=int)}
    companies = db.company_choices()
    errors = {}
    if request.method == "POST":
        data, errors = validate_contact(request.form, {c["company_id"] for c in companies})
        if not errors:
            if contact_id:
                db.update_contact(contact_id, data)
                flash(f"Updated {data['contact_name']}.", "success")
            else:
                contact_id = db.create_contact(data)
                flash(f"Added {data['contact_name']}.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        contact = {**request.form, "company_id": request.form.get("company_id", type=int)}
    if not companies:
        flash("Add a company before adding contacts.", "info")
        return redirect(url_for("company_form"))
    return render_template("contact_form.html", contact=contact, contact_id=contact_id,
                           companies=companies, errors=errors)


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = get_or_404(db.get_contact(contact_id))
    db.delete_contact(contact_id)
    flash(f"Deleted {contact['contact_name']}.", "success")
    return redirect(url_for("contacts"))


# ---------------------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------------------
@app.route("/job-match")
def job_match():
    skills_text = request.args.get("skills", "")
    min_percent = request.args.get("min", 0, type=int)
    skills = parse_skills(skills_text)
    results = match_jobs(skills, db.get_jobs_for_matching(), min_percent) if skills else []
    return render_template("job_match.html", skills_text=skills_text, skills=skills,
                           results=results, min_percent=min_percent,
                           submitted="skills" in request.args)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1",
            port=int(os.getenv("PORT", "5001")))
