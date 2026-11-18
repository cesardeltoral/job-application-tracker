from matching import match_jobs, normalize, parse_skills


def job(title, required, preferred=None):
    return {"job_title": title,
            "requirements": {"required_skills": required, "preferred_skills": preferred or []}}


def test_spec_example():
    """Mirrors the example in the project specification."""
    jobs = [job("Data Analyst", ["Python", "SQL", "Tableau"]),
            job("Software Developer", ["Python", "SQL", "Flask"])]
    results = match_jobs(["Python", "SQL", "Flask"], jobs)

    assert [r["job"]["job_title"] for r in results] == ["Software Developer", "Data Analyst"]
    assert results[0]["percent"] == 100
    assert results[1]["percent"] == 67
    assert results[1]["missing"] == ["Tableau"]


def test_case_whitespace_and_aliases():
    assert normalize("  PyThOn ") == "python"
    assert normalize("JS") == "javascript"
    result = match_jobs(["js", "postgres"], [job("Web", ["JavaScript", "PostgreSQL"])])[0]
    assert result["percent"] == 100


def test_jobs_without_requirements_are_skipped():
    assert match_jobs(["Python"], [{"job_title": "X", "requirements": {}}]) == []


def test_min_percent_filter():
    jobs = [job("A", ["Python"]), job("B", ["Java"])]
    assert [r["job"]["job_title"] for r in match_jobs(["Python"], jobs, min_percent=50)] == ["A"]


def test_tie_broken_by_preferred_skills():
    jobs = [job("Plain", ["SQL"]), job("Bonus", ["SQL"], ["Docker"])]
    results = match_jobs(["SQL", "Docker"], jobs)
    assert results[0]["job"]["job_title"] == "Bonus"
    assert results[0]["preferred_matched"] == ["Docker"]


def test_parse_skills_dedupes_and_splits():
    assert parse_skills("Python, sql;\nPYTHON ,  Flask  ") == ["Python", "sql", "Flask"]
    assert parse_skills("") == []
