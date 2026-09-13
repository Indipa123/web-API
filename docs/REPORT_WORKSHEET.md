# Write your own report: planning worksheet

This is a worksheet, not report prose for submission. The supplied brief permits declared AI-generated code but excludes AI-generated report prose. Write your explanations yourself from your actual work and understanding. Do not sign someone else's declaration or copy this worksheet as your report.

Target: 2,500 words, permitted range 2,250–2,750. The official declaration, AI appendix, diagrams, tables, code listings and references are outside the stated word count. Confirm the LMS deadline and required submission file format.

| Required section | Suggested words | Questions to answer in your own words | Evidence to collect |
|---|---:|---|---|
| Architecture and data model | 450 | What are the six entities? Why is meter ID an attribute? Why is a reading a separate row? How do foreign keys protect the hierarchy? Why SQLite for this implementation? | Your ER diagram; table definitions and real counts |
| API design justification | 650 | Why these resource names and nesting? What is atomic, collection, composite or derived? Why POST/201/Location? Where are PUT, DELETE, 409, 412 and 304 appropriate? How do paging/filter/sort work? | Endpoint table, real requests and response headers; module guideline references |
| Security justification | 450 | How is the meter linked to its installation? Where is human read scope enforced? Can a filter bypass that scope? Why 401/403/404? How are credentials kept private? What are the limitations? | Denied cross-district and cross-meter requests; relevant code |
| Deployment | 300 | Where did you actually deploy? How does it start? How do you preserve data? How did you prove HTTPS, documentation and persistence? | Actual URL, deployment settings, commit hash and restart check |
| Richardson maturity | 250 | How do named resources demonstrate Level 1? How do methods and status codes demonstrate Level 2? Why do pagination links alone not establish Level 3 hypermedia? | Specific endpoints and response examples |
| Critical evaluation | 400 | What works? Which tests support that? What is not implemented? How would you improve scale, security, caching and summaries? | Actual test result; honest limitations and prioritized improvements |

Total suggested words: 2,500.

## Decisions to investigate and explain

- Event time versus arrival time: `last-known-reading` uses the timestamp, so a delayed older reading does not become the latest.
- Readings are append-only in both routes and database triggers. Meter reset handling has deliberately not been implemented; decreased cumulative values are rejected.
- A district summary sums only sufficiently fresh power readings. Energy uses differences in cumulative measurements around the start of the local day; gaps around midnight make this an estimate.
- Authentication precedes protected resource retrieval and ETag comparison. Out-of-scope cached data must not be revealed by a 304 response.
- Queries combine authorization and requested filters using AND. User-supplied SQL fragments are never accepted.
- SQLite's indexes help reading history, but offset paging and per-installation summary queries would need improvement at national scale.
- Bearer API credentials simplify a coursework demonstration. Real staff identity should use organizational identity/OIDC; real deployment also needs token rotation/revocation, rate limits, audit logging and backups.
- Seed generation runs once. Seed data ages and is not a continuous live-meter simulator. Use real new POSTs for fresh readings in a demonstration.
- ETag implements conditional GET. Last-Modified is not implemented; check whether the missing module guidelines require it in addition to ETag.
- The provisioning principal is an explicit interpretation of the CRUD requirement alongside the strict device/user split. Verify with your lecturer before final submission.

## Before writing

Obtain the module's REST API Design Guidelines and the separate marking rubric. Those were referenced by the brief but were not included with it. Compare each design decision with the actual sections; do not invent quotations or page citations from missing documents.

Read and cite the sources you actually use. Keep implementation references separate from the module's design authority. Use your course's required referencing style.

## Final submission checklist

- [ ] Public HTTPS API works with seeded data.
- [ ] Live Swagger/OpenAPI works from the deployment.
- [ ] Remote repository contains real incremental history.
- [ ] Module leader has collaborator access.
- [ ] Report is in the required word range and contains all six identifiable sections.
- [ ] Official coursework declaration is completed and signed by you.
- [ ] AI disclosure includes prompts and assistance references.
- [ ] Actual deployment and test evidence is included.
- [ ] You can explain every submitted feature and code section.
- [ ] You have checked the LMS deadline and attended/prepared for the viva.
