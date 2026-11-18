"""End-to-end tests: every page and full CRUD for all four tables.

These tests write to MySQL, so they only run when RUN_DB_TESTS=1 is set,
against the database configured in .env (load it with schema.sql first).
Every record they create is deleted again at the end.

    RUN_DB_TESTS=1 pytest tests/test_app.py -v
"""

import os

import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1",
                                reason="set RUN_DB_TESTS=1 to run database tests")


@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def new_id(response):
    assert response.status_code == 302, response.data[:500]
    return int(response.headers["Location"].rstrip("/").rsplit("/", 1)[1])


@pytest.mark.parametrize("url", [
    "/", "/companies", "/companies?q=a", "/companies/new",
    "/jobs", "/jobs?type=Internship", "/jobs/new",
    "/applications", "/applications?status=Interview", "/applications/new",
    "/contacts", "/contacts/new",
    "/job-match", "/job-match?skills=Python,SQL,Flask&min=50",
])
def test_pages_load(client, url):
    assert client.get(url).status_code == 200


def test_missing_record_is_404(client):
    assert client.get("/companies/999999").status_code == 404


def test_delete_requires_post(client):
    assert client.get("/companies/1/delete").status_code == 405


def test_full_crud_and_cascade(client):
    import database as db

    # Company: validation, create (with an apostrophe), update
    r = client.post("/companies/new", data={"company_name": "", "website": "nope"})
    assert b"is required" in r.data and b"http://" in r.data
    cid = new_id(client.post("/companies/new", data={
        "company_name": "O'Reilly Test Labs", "industry": "Media",
        "website": "https://oreilly.example.com"}))
    assert b"O&#39;Reilly Test Labs" in client.get(f"/companies/{cid}").data
    assert b"already exists" in client.post("/companies/new",
                                            data={"company_name": "O'Reilly Test Labs"}).data
    new_id(client.post(f"/companies/{cid}/edit", data={"company_name": "O'Reilly Test Labs",
                                                        "industry": "Publishing"}))
    assert db.get_company(cid)["industry"] == "Publishing"

    try:
        # Job: salary validation, JSON requirements round-trip, update
        r = client.post("/jobs/new", data={"company_id": cid, "job_title": "X",
                                           "salary_min": "9", "salary_max": "1"})
        assert b"greater than or equal" in r.data
        jid = new_id(client.post("/jobs/new", data={
            "company_id": cid, "job_title": "Tech Writer", "job_type": "Contract",
            "required_skills": "Writing, Markdown", "remote_option": "on"}))
        assert db.get_job(jid)["requirements"] == {
            "required_skills": ["Writing", "Markdown"], "remote_option": True}
        new_id(client.post(f"/jobs/{jid}/edit", data={
            "company_id": cid, "job_title": "Technical Writer", "job_type": "Full-time",
            "required_skills": "Writing"}))
        assert db.get_job(jid)["job_title"] == "Technical Writer"

        # Job match finds the new job at 100%
        assert b"Technical Writer" in client.get("/job-match?skills=writing&min=100").data

        # Application: future date rejected, JSON interview data round-trip, update, delete
        r = client.post("/applications/new", data={"job_id": jid, "application_date": "2999-01-01"})
        assert b"cannot be in the future" in r.data
        aid = new_id(client.post("/applications/new", data={
            "job_id": jid, "application_date": "2026-11-10", "status": "Interview",
            "cover_letter_sent": "on", "interviewers": "Ann Lee, Bo Kim", "rating": "4"}))
        app_row = db.get_application(aid)
        assert app_row["interview_data"] == {"interviewers": ["Ann Lee", "Bo Kim"], "rating": 4}
        assert app_row["cover_letter_sent"] == 1
        new_id(client.post(f"/applications/{aid}/edit", data={
            "job_id": jid, "application_date": "2026-11-10", "status": "Offer"}))
        assert db.get_application(aid)["status"] == "Offer"
        assert client.post(f"/applications/{aid}/delete").status_code == 302
        assert db.get_application(aid) is None

        # Contact: email validation, create, update, delete
        r = client.post("/contacts/new", data={"company_id": cid, "contact_name": "A",
                                               "email": "bad"})
        assert b"valid email" in r.data
        kid = new_id(client.post("/contacts/new", data={
            "company_id": cid, "contact_name": "Ann Lee", "email": "ann@example.com"}))
        new_id(client.post(f"/contacts/{kid}/edit", data={
            "company_id": cid, "contact_name": "Ann Lee", "title": "Editor"}))
        assert db.get_contact(kid)["title"] == "Editor"
        assert client.post(f"/contacts/{kid}/delete").status_code == 302
        assert db.get_contact(kid) is None

        # Cascade: deleting the company removes its job and that job's applications
        aid2 = new_id(client.post("/applications/new", data={
            "job_id": jid, "application_date": "2026-11-10", "status": "Applied"}))
    finally:
        client.post(f"/companies/{cid}/delete")

    assert db.get_company(cid) is None
    assert db.get_job(jid) is None
    assert db.get_application(aid2) is None
