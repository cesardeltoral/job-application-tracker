from datetime import date, timedelta

from validators import (validate_application, validate_company, validate_contact,
                        validate_job)


def test_company_requires_name_and_valid_url():
    _, errors = validate_company({"company_name": "  ", "website": "techcorp.com"})
    assert "company_name" in errors
    assert "website" in errors


def test_company_valid():
    data, errors = validate_company({"company_name": "TechCorp", "website": "https://t.co"})
    assert errors == {}
    assert data["industry"] is None


def test_job_salary_range_and_company():
    _, errors = validate_job({"company_id": "1", "job_title": "Dev",
                              "salary_min": "90000", "salary_max": "50000"}, {1})
    assert "salary_max" in errors
    _, errors = validate_job({"company_id": "99", "job_title": "Dev"}, {1})
    assert "company_id" in errors


def test_job_builds_requirements_json():
    data, errors = validate_job({"company_id": "1", "job_title": "Dev", "job_type": "Contract",
                                 "required_skills": "Python, SQL", "experience_years": "2",
                                 "remote_option": "on"}, {1})
    assert errors == {}
    assert data["requirements"] == {"required_skills": ["Python", "SQL"],
                                    "experience_years": 2, "remote_option": True}


def test_job_rejects_bad_enum():
    _, errors = validate_job({"company_id": "1", "job_title": "Dev", "job_type": "Gig"}, {1})
    assert "job_type" in errors


def test_application_rejects_future_date_and_bad_rating():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _, errors = validate_application({"job_id": "1", "application_date": tomorrow,
                                      "status": "Applied", "rating": "9"}, {1})
    assert "application_date" in errors
    assert "rating" in errors


def test_application_interview_json_omits_empty_fields():
    data, errors = validate_application({"job_id": "1", "application_date": "2026-10-01",
                                         "status": "Interview", "interviewers": "Ann, Bo",
                                         "technical_questions": "Joins\n\nIndexes"}, {1})
    assert errors == {}
    assert data["interview_data"] == {"interviewers": ["Ann", "Bo"],
                                      "technical_questions": ["Joins", "Indexes"]}
    assert data["cover_letter_sent"] is False


def test_contact_email_and_phone():
    _, errors = validate_contact({"company_id": "1", "contact_name": "Ann",
                                  "email": "not-an-email", "phone": "abc"}, {1})
    assert set(errors) == {"email", "phone"}
