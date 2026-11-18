# Job Application Tracker

A full-stack web app for tracking a job search: the companies you're targeting, the jobs they've posted, your applications and interviews, and the people you know there. A **Job Match** page ranks every job by how many of its required skills you have.

**Stack:** MySQL 8 · Python 3 · Flask · HTML/CSS (no CSS framework)

> 📹 **Demo video (5 min):** [Watch on Google Drive](https://drive.google.com/file/d/1czestcDvQve8MQxw6_5Ls22-Q2KW2Z_y/view?usp=sharing)
> Walkthrough of the database, the Flask server and the client. The same video is in this repo as [`demo.mp4`](demo.mp4).

## Features

| Page | What it does |
|------|--------------|
| **Dashboard** | Totals, response rate, applications by status, most-requested skills (computed with `JSON_TABLE`), recent applications and upcoming next steps |
| **Companies** | List / search / detail / add / edit / delete. The detail page shows the company's jobs, contacts and applications |
| **Jobs** | List / search / filter by type / detail / add / edit / delete. Requirements (skills, education, experience, remote) are stored in a JSON column |
| **Applications** | List / filter by status / search / detail / add / edit / delete. Interview rounds, interviewers, questions, feedback, next steps and rating are stored in a JSON column |
| **Contacts** | List / search / detail / add / edit / delete |
| **Job Match** | Enter your skills and see jobs ranked by match %, with matched, missing and bonus (preferred) skills |

Validation runs on the server for every form: required fields, max lengths, URL/email/phone formats, salary min ≤ max, no future application dates, valid ENUM values, and foreign keys that must point to existing rows. Deletes are POST-only and ask for confirmation first.

## Setup (fresh clone)

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0.16+ running locally (needed for `JSON_TABLE` and enforced `CHECK` constraints)

### 2. Clone and install
```bash
git clone https://github.com/cesardeltoral/job-application-tracker.git
cd job-application-tracker

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create the database
```bash
mysql -u root -p < schema.sql
```
This creates the `job_tracker` database, the four tables, a view and sample data.
You can also open `schema.sql` in MySQL Workbench and run it with the ⚡ button.

> ⚠️ `schema.sql` drops and recreates the `companies`, `jobs`, `applications` and `contacts` tables inside `job_tracker`.

### 4. Configure credentials
```bash
cp .env.example .env               # Windows: copy .env.example .env
```
Then edit `.env` and set `DB_PASSWORD` to your MySQL root password (and `DB_USER` if you don't use root).

### 5. Run
```bash
python app.py
```
Open **http://127.0.0.1:5001**.

The app uses port 5001 because macOS uses port 5000 for AirPlay. To use another port, change `PORT` in `.env`.

### 6. Run the tests (optional)
```bash
pytest                                  # unit tests: job match + validation (no database needed)
RUN_DB_TESTS=1 pytest tests/test_app.py # end-to-end: every page + CRUD on all 4 tables
```
The end-to-end tests use the database in `.env`. They create their own records and delete them at the end.

## How Job Match works

```
match % = (required skills you have) / (total required skills for the job) × 100
```

- Skills are compared case-insensitively with extra whitespace ignored, and common aliases count as the same skill (`JS` = `JavaScript`, `Postgres` = `PostgreSQL`, …).
- Jobs are sorted by match %. Ties go to the job with more matched skills, then more matched *preferred* skills.
- Each result lists the skills you have, the skills you're missing, and any bonus preferred skills.

Example with the sample data and skills `Python, SQL, Flask`:
```
1. Software Developer at TechCorp – 100% (3/3 skills)
2. Data Analyst at DataCo         –  67% (2/3 skills)   Missing: Tableau
3. Full Stack Developer at CloudNine Systems – 60% (3/5 skills)   Missing: JavaScript, React
```

The algorithm is in `matching.py`, kept separate from Flask so it can be unit tested.

## Database design

```
companies 1───* jobs 1───* applications
    │
    └──────* contacts
```

| Table | Key points |
|-------|------------|
| `companies` | `company_name` is NOT NULL and UNIQUE |
| `jobs` | FK → companies (ON DELETE CASCADE), `job_type` ENUM, `CHECK (salary_min <= salary_max)`, `requirements` JSON |
| `applications` | FK → jobs (ON DELETE CASCADE), `status` ENUM, `cover_letter_sent` BOOLEAN, `interview_data` JSON, indexes on status and date |
| `contacts` | FK → companies (ON DELETE CASCADE) |
| `application_overview` (view) | Joins applications → jobs → companies. The Applications pages read from it |

JSON column shapes:
```json
// jobs.requirements
{"required_skills": ["Python", "SQL"], "preferred_skills": ["Docker"],
 "education": "Bachelor in CS", "experience_years": 2, "remote_option": true}

// applications.interview_data
{"interview_rounds": 2, "interviewers": ["Sarah Johnson"], "technical_questions": ["SQL joins"],
 "feedback": "Strong technical skills", "next_steps": "Final round scheduled", "rating": 4}
```
The forms show these as ordinary fields, such as comma-separated skills. The server turns them into JSON and leaves empty keys out.

## Project structure

```
job-application-tracker/
├── app.py              # Flask routes (dashboard, CRUD for 4 tables, job match)
├── database.py         # MySQL connection + parameterized query functions
├── validators.py       # Server-side form validation
├── matching.py         # Job match algorithm
├── schema.sql          # Creates the database, tables, view and sample data
├── templates/          # Jinja2 HTML templates (base layout + one per page/form)
├── static/style.css    # All styling
├── tests/              # pytest unit tests
├── AI_USAGE.md         # How generative AI was used on this project
├── requirements.txt
└── .env.example        # Copy to .env and add your MySQL password
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Access denied for user 'root'` | `DB_PASSWORD` in `.env` is wrong |
| `Unknown database 'job_tracker'` | Run `mysql -u root -p < schema.sql` |
| `Can't connect to MySQL server` | Start MySQL (macOS: System Settings → MySQL; Windows: Services → MySQL80) |
| `Address already in use` | Change `PORT` in `.env` |
| `ModuleNotFoundError: flask` | Activate the virtual env, then `pip install -r requirements.txt` |
