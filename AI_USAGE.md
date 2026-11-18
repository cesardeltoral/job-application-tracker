# AI Usage Documentation

## Tools Used

I used **Claude Code (Anthropic)** as an AI coding assistant in the terminal. It can inspect project files, suggest code, run commands, and help troubleshoot problems. I used it as a supporting resource while developing my Flask and MySQL project, rather than treating its suggestions as finished work.

## How I Worked With AI

I started with the assignment description, `Project_Specification.docx`, and my previous work in `assignments1-8.zip`. These were the source of truth for the database schema, JSON structures, and grading requirements. I organized the work into stages: schema, database access, validation, job matching, routes, templates, testing, and documentation.

I remained responsible for understanding the requirements, deciding how the pieces should fit together, reviewing the implementation, and checking that the finished application worked. Claude Code helped me think through design choices, generate or refine repetitive code, and identify potential errors. I evaluated its suggestions against the specification and the behavior of the running application.

I used Git commits to keep the stages of development organized. Testing and browser checks were important parts of my workflow: I used unit tests and a separate local MySQL test instance to verify CRUD operations without affecting my main database, and I reviewed the pages visually.

## Key Prompts and AI Assistance

My initial prompt included the assignment description and asked Claude Code to inspect the downloaded specification and previous assignments, then help plan the project.

Examples of the kinds of questions and requests I used during development (paraphrased):

- "Check whether my four-table schema, foreign keys, and JSON columns match the specification and Assignment 7."
- "Help me review the database CRUD functions for parameterized queries and proper connection handling."
- "Suggest a clear way to calculate job-match percentages and display matched and missing skills."
- "Review the server-side form validation for required fields, lengths, URLs, emails, salary ranges, ENUM values, and foreign keys."
- "How can I make JSON data editable through normal form fields instead of asking users to type raw JSON?"
- "Help me troubleshoot this failing test or template error, and explain the cause."

These examples describe how I used AI for feedback and targeted assistance; they are not a verbatim record of every prompt.

## What AI Helped With

**Repetitive code and consistency.** The four tables share similar list, detail, form, and delete workflows. Claude Code was useful for suggesting reusable patterns and reviewing shared Jinja macros in `templates/_macros.html` so the forms stayed consistent.

**Checking course requirements.** Referring to the original assignment files helped me verify that JSON fields such as `required_skills`, `interview_rounds`, and `interviewers` followed the structures used in class.

**Exploring MySQL features.** AI suggestions helped me consider `JSON_TABLE` for dashboard skill counts, a `CHECK` constraint for salary ranges, and an `application_overview` view. I still needed to understand how each feature worked and whether it fit the project.

**Debugging and test review.** Claude Code helped interpret error messages, propose fixes, and identify cases worth testing. I treated passing tests and actual application behavior as the evidence that a fix worked.

## Problems I Reviewed and Fixed

The project needed several corrections during implementation and testing:

- **Inconsistent salary units:** Some internship sample records used hourly rates while the other records used annual salaries. I standardized the sample data to annual amounts.
- **Invalid Jinja filter:** A job form used a `zip` filter that was not available by default in Jinja2. The solution was to register a custom `choices` filter in `app.py`.
- **Navigation highlighting:** Both "Jobs" and "Job Match" could appear active because of a prefix-based comparison. I changed the logic to use explicit page groups.
- **Apostrophes in delete confirmations:** A company name such as `O'Reilly Labs` could break a JavaScript confirmation string. Using Jinja's `tojson` escaping fixed the issue, and I included an apostrophe case in `tests/test_app.py`.
- **Whitespace in a macro:** Extra whitespace prevented an `or '—'` fallback from appearing. Jinja whitespace-control syntax resolved it.
- **Port conflict:** On macOS, AirPlay can occupy port 5000. I configured the Flask app to default to port 5001, with an override in `.env`.
- **MySQL test socket path:** A long temporary socket path prevented the test database from starting. Shortening the path resolved the MySQL socket-length issue.

These examples reinforced why I needed to inspect generated suggestions, run the application, and verify fixes instead of assuming the first answer was correct.

## Lessons Learned

**Use the original specification.** Keeping the assignment instructions and earlier course files available made it easier to check whether my implementation satisfied the required schema and JSON formats.

**AI is useful for feedback, not proof of correctness.** A suggestion can look reasonable and still fail at runtime. Tests, database checks, and browser reviews were more reliable than accepting an explanation alone.

**Build in manageable stages.** Separating the database layer, validation, matching logic, routes, and templates made the project easier to understand and debug.

**Keep business logic testable.** Isolating the matching algorithm and validation in `matching.py` and `validators.py` made it possible to test important behavior without depending on the full Flask app or MySQL connection.

**Understand the underlying code.** I focused on being able to explain parameterized SQL queries (`%s` placeholders), foreign-key behavior such as `ON DELETE CASCADE`, and how `JSON_TABLE` converts JSON arrays into relational rows.

## My Own Notes

I was the main developer and took responsibility for the project's requirements, structure, implementation decisions, and final verification. Claude Code served as an assistant when I wanted a second opinion, help with repetitive patterns, or an explanation of an error. I did not treat its output as automatically correct; I reviewed suggestions and made changes based on the specification and my tests.

One of the most useful habits I developed was testing against a disposable MySQL instance instead of risking changes to my main database. I also learned to verify both backend behavior and the actual rendered pages, because several issues only became visible when the application was running.

If I were to improve my workflow, I would document my design decisions and test cases earlier, before adding more routes and templates. That would make it easier to distinguish intentional behavior from accidental behavior and to track why I made each change.

I want to be able to explain every major part of the finished project: why SQL uses `%s` placeholders instead of string interpolation, what happens to related jobs and applications when a company is deleted, how the Job Match percentage is calculated, and why the JSON columns are edited through regular form inputs.
