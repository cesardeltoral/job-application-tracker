"""Job Match: rank jobs by how many of their required skills the user has.

match % = (required skills the user has) / (total required skills) * 100

Skill comparison is case-insensitive, ignores extra whitespace, and treats a
few common aliases as the same skill (e.g. "JS" and "JavaScript").
"""

import re

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "rest": "rest apis",
    "rest api": "rest apis",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "amazon web services": "aws",
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
}


def normalize(skill):
    """Lower-case, collapse whitespace and resolve aliases."""
    key = " ".join(str(skill).strip().lower().split())
    return ALIASES.get(key, key)


def parse_skills(text):
    """Split free text on commas, semicolons or new lines into a de-duplicated list."""
    seen, skills = set(), []
    for part in re.split(r"[,;\n]+", text or ""):
        part = " ".join(part.split())
        if part and normalize(part) not in seen:
            seen.add(normalize(part))
            skills.append(part)
    return skills


def score_job(user_skills, job):
    """Return a match dict for one job, or None if the job lists no required skills."""
    requirements = job.get("requirements") or {}
    required = requirements.get("required_skills") or []
    if not required:
        return None

    have = {normalize(s) for s in user_skills}
    matched = [s for s in required if normalize(s) in have]
    missing = [s for s in required if normalize(s) not in have]
    preferred = requirements.get("preferred_skills") or []
    preferred_matched = [s for s in preferred if normalize(s) in have]

    return {
        "job": job,
        "matched": matched,
        "missing": missing,
        "preferred_matched": preferred_matched,
        "required_count": len(required),
        "percent": round(100 * len(matched) / len(required)),
    }


def match_jobs(user_skills, jobs, min_percent=0):
    """Score every job and return results sorted best match first.

    Ties are broken by number of matched required skills, then matched
    preferred skills, then job title.
    """
    results = []
    for job in jobs:
        result = score_job(user_skills, job)
        if result is not None and result["percent"] >= min_percent:
            results.append(result)

    results.sort(
        key=lambda r: (
            -r["percent"],
            -len(r["matched"]),
            -len(r["preferred_matched"]),
            r["job"].get("job_title", "").lower(),
        )
    )
    return results
