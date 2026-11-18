-- =====================================================================
-- Job Application Tracker - database creation script
-- Run with:  mysql -u root -p < schema.sql
-- WARNING: drops and recreates the four tracker tables in job_tracker.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS job_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE job_tracker;

-- Drop in reverse dependency order so foreign keys don't block us
DROP VIEW  IF EXISTS application_overview;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

-- ---------------------------------------------------------------------
-- companies: organizations the user is applying to
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT          PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    CONSTRAINT uq_company_name UNIQUE (company_name)
);

-- ---------------------------------------------------------------------
-- jobs: positions posted by a company
-- requirements JSON shape:
--   {"required_skills": [...], "preferred_skills": [...],
--    "education": "...", "experience_years": 2, "remote_option": true}
-- ---------------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT          PRIMARY KEY AUTO_INCREMENT,
    company_id   INT          NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salary_nonneg CHECK (salary_min IS NULL OR salary_min >= 0),
    CONSTRAINT chk_salary_range  CHECK (salary_min IS NULL OR salary_max IS NULL
                                        OR salary_min <= salary_max)
);

CREATE INDEX idx_jobs_title ON jobs (job_title);

-- ---------------------------------------------------------------------
-- applications: the user's application to a specific job
-- interview_data JSON shape:
--   {"interview_rounds": 2, "interviewers": [...], "technical_questions": [...],
--    "feedback": "...", "next_steps": "...", "rating": 4}
-- ---------------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT  PRIMARY KEY AUTO_INCREMENT,
    job_id            INT  NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn')
                      NOT NULL DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_applications_date   ON applications (application_date);

-- ---------------------------------------------------------------------
-- contacts: people the user knows at a company
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT          PRIMARY KEY AUTO_INCREMENT,
    company_id   INT          NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies (company_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ---------------------------------------------------------------------
-- View: one row per application with its job and company joined in
-- ---------------------------------------------------------------------
CREATE VIEW application_overview AS
SELECT a.application_id,
       a.application_date,
       a.status,
       a.resume_version,
       a.cover_letter_sent,
       a.interview_data,
       j.job_id,
       j.job_title,
       j.job_type,
       c.company_id,
       c.company_name
FROM applications a
JOIN jobs      j ON j.job_id = a.job_id
JOIN companies c ON c.company_id = j.company_id;

-- =====================================================================
-- Sample data
-- =====================================================================
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',         'Software',    'https://techcorp.example.com',    'Miami',         'FL', 'Fast-growing SaaS startup. Hybrid schedule.'),
('DataCo',           'Analytics',   'https://dataco.example.com',      'Austin',        'TX', 'Strong data culture, good mentorship program.'),
('CloudNine Systems','Cloud',       'https://cloudnine.example.com',   'Seattle',       'WA', NULL),
('HealthBridge',     'Healthcare',  'https://healthbridge.example.com','Orlando',       'FL', 'Met a recruiter at the campus career fair.'),
('FinEdge',          'Finance',     'https://finedge.example.com',     'New York',      'NY', 'Requires a coding assessment before interviews.'),
('GreenGrid Energy', 'Energy',      'https://greengrid.example.com',   'Denver',        'CO', NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',        'Full-time',  75000,  95000, 'https://techcorp.example.com/careers/101',   '2026-09-15',
   '{"required_skills": ["Python", "SQL", "Flask"], "preferred_skills": ["Docker", "AWS"], "education": "Bachelor in CS or related field", "experience_years": 1, "remote_option": true}'),
(2, 'Data Analyst',              'Full-time',  65000,  80000, 'https://dataco.example.com/jobs/analyst',    '2026-09-20',
   '{"required_skills": ["Python", "SQL", "Tableau"], "preferred_skills": ["R", "Excel"], "education": "Bachelor degree", "experience_years": 1, "remote_option": false}'),
(3, 'Cloud Engineer Intern',     'Internship', 42000,  50000,  'https://cloudnine.example.com/interns',      '2026-10-01',
   '{"required_skills": ["Linux", "AWS", "Python"], "preferred_skills": ["Terraform", "Docker"], "education": "Pursuing Bachelor in CS", "experience_years": 0, "remote_option": true}'),
(4, 'Database Administrator',    'Full-time',  80000, 100000, 'https://healthbridge.example.com/jobs/dba',  '2026-09-28',
   '{"required_skills": ["MySQL", "SQL", "Backup and Recovery", "Linux"], "preferred_skills": ["PostgreSQL", "Python"], "education": "Bachelor degree", "experience_years": 2, "remote_option": false}'),
(5, 'Junior Backend Developer',  'Full-time',  85000, 105000, 'https://finedge.example.com/careers/backend','2026-10-05',
   '{"required_skills": ["Java", "SQL", "REST APIs", "Git"], "preferred_skills": ["Spring Boot", "Kafka"], "education": "Bachelor in CS", "experience_years": 1, "remote_option": false}'),
(1, 'QA Automation Engineer',    'Contract',   60000,  75000, 'https://techcorp.example.com/careers/115',   '2026-10-10',
   '{"required_skills": ["Python", "Selenium", "Git"], "preferred_skills": ["CI/CD"], "education": "Any", "experience_years": 1, "remote_option": true}'),
(6, 'Data Engineer',             'Full-time',  90000, 115000, 'https://greengrid.example.com/jobs/de',      '2026-10-12',
   '{"required_skills": ["Python", "SQL", "Spark", "Airflow"], "preferred_skills": ["AWS", "Kafka"], "education": "Bachelor degree", "experience_years": 2, "remote_option": true}'),
(2, 'Business Intelligence Intern','Internship', 38000,  44000,  'https://dataco.example.com/jobs/bi-intern',  '2026-10-15',
   '{"required_skills": ["SQL", "Excel"], "preferred_skills": ["Power BI", "Tableau"], "education": "Pursuing Bachelor degree", "experience_years": 0, "remote_option": false}'),
(4, 'IT Support Specialist',     'Part-time',  35000,  45000, NULL,                                         '2026-10-20',
   '{"required_skills": ["Troubleshooting", "Windows", "Customer Service"], "preferred_skills": ["Linux"], "education": "Associate degree", "experience_years": 0, "remote_option": false}'),
(3, 'Full Stack Developer',      'Full-time',  95000, 120000, 'https://cloudnine.example.com/jobs/fullstack','2026-11-01',
   '{"required_skills": ["JavaScript", "React", "Python", "SQL", "Flask"], "preferred_skills": ["Docker", "AWS"], "education": "Bachelor in CS", "experience_years": 2, "remote_option": true}');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-09-18', 'Interview', 'v2-software', TRUE,
   '{"interview_rounds": 2, "interviewers": ["Sarah Johnson", "Mike Chen"], "technical_questions": ["SQL joins", "Python basics", "API design"], "feedback": "Strong technical skills, good communication", "next_steps": "Final round scheduled", "rating": 4}'),
(2, '2026-09-22', 'Screening', 'v1-data',     FALSE, NULL),
(3, '2026-10-03', 'Applied',   'v2-software', TRUE,  NULL),
(4, '2026-10-01', 'Rejected',  'v1-general',  TRUE,
   '{"interview_rounds": 1, "interviewers": ["Emily Williams"], "technical_questions": ["Database normalization", "Transaction isolation"], "feedback": "Needs more experience with cloud platforms", "rating": 3}'),
(5, '2026-10-07', 'Applied',   'v2-software', FALSE, NULL),
(7, '2026-10-14', 'Offer',     'v3-data',     TRUE,
   '{"interview_rounds": 3, "interviewers": ["Raj Patel", "Lena Ortiz"], "technical_questions": ["Spark partitioning", "Window functions"], "feedback": "Great culture fit", "next_steps": "Review offer by Nov 25", "rating": 5}'),
(8, '2026-10-16', 'Withdrawn', 'v1-data',     FALSE, NULL),
(10,'2026-11-03', 'Applied',   'v3-fullstack',TRUE,  NULL),
(6, '2026-10-12', 'Screening', 'v2-software', FALSE,
   '{"interview_rounds": 1, "interviewers": ["Tom Baker"], "next_steps": "Take-home assignment due Nov 20"}');

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Sarah Johnson',  'Engineering Manager',  'sarah.johnson@techcorp.example.com', '305-555-0142', 'https://www.linkedin.com/in/example-sjohnson', 'Hiring manager for the Software Developer role.'),
(1, 'Mike Chen',      'Senior Developer',     'mike.chen@techcorp.example.com',     NULL,           NULL,                                            'Ran the technical interview.'),
(2, 'Priya Desai',    'Recruiter',            'priya@dataco.example.com',           '512-555-0199', 'https://www.linkedin.com/in/example-pdesai',   'Follow up every two weeks.'),
(4, 'Emily Williams', 'DBA Team Lead',        'ewilliams@healthbridge.example.com', '407-555-0110', NULL,                                            NULL),
(5, 'Daniel Brooks',  'Talent Acquisition',   'dbrooks@finedge.example.com',        '212-555-0175', 'https://www.linkedin.com/in/example-dbrooks',  'Met at the career fair.'),
(6, 'Lena Ortiz',     'Director of Data',     'lena.ortiz@greengrid.example.com',   '720-555-0133', NULL,                                            'Sent the offer letter.');
