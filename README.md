# Solar Generation API — start here

A working coursework implementation for NB6007CEM. It contains the backend, synthetic seed generator, Swagger interface, tests, Docker deployment files and learning notes. There is no dashboard because the brief asks for the API only.

**Status:** built, tested and published to [your coursework branch](https://github.com/Indipa123/web-API/tree/coursework/solar-api). Public hosting, the collaborator invitation, your own report, signed declaration and viva remain to be completed. Read `docs/VERIFICATION.md` for the actual checks performed. A live deployment is essential; running on your laptop alone does not complete the assignment.

## 1. Open the project

To obtain a fresh copy with the Git history, use:

```sh
git clone --branch coursework/solar-api https://github.com/Indipa123/web-API.git solar-api
cd solar-api
```

The ZIP download contains source files only. Use the clone command above if you want to commit and push changes. The already-created local project folder includes its Git history.

Open this `solar-api` folder in VS Code. Select Terminal → New Terminal. Commands below assume the terminal is inside this folder. Use Python 3.12 or newer (the project was tested with 3.12).

On a Mac:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` after creating it with `py -3.12 -m venv .venv`.

**What this does:** creates a private Python environment and installs the server and testing libraries.

## 2. Create the demonstration data

```sh
python -m app.seed
```

**Expected:** “Seed created; credentials saved privately.” Repeating the command safely does nothing if data already exists.

The data contains 9 provinces, 25 districts, 25 illustrative substations, 200 synthetic installations and 134,600 readings. Each installation has 673 points at 15-minute intervals spanning seven full days. Nighttime generation is zero in Sri Lankan local time. The database is `data/solar.db`; random bearer credentials are saved in `data/credentials.json`. Neither file belongs in Git.

## 3. Start the API

```sh
python -m uvicorn app.main:app --reload
```

Leave that terminal running. Open <http://127.0.0.1:8000/docs> in a browser.

**What you see:** Swagger, the interactive API documentation. Expand an endpoint, select “Try it out”, enter parameters and select “Execute”. To stop the server later, press Ctrl+C.

## 4. Log in as a reader

Open `data/credentials.json` locally. Copy the value of `user_1_national`. In Swagger, select **Authorize**, paste just that token, and authorize it. The browser adds `Authorization: Bearer ...` to requests.

Try these in order:

1. `GET /api/v1/provinces` → 9 provinces.
2. `GET /api/v1/provinces/1/districts` → the 3 Western Province districts.
3. `GET /api/v1/districts/1/grid-substations` → the Colombo demonstration substation.
4. `GET /api/v1/grid-substations/1/installations` → 8 installations.
5. `GET /api/v1/installations/1/overview` → an installation, its hierarchy and latest reading.
6. `GET /api/v1/installations/1/last-known-reading` → one latest observation.
7. `GET /api/v1/installations/1/readings`, with `page_size=2` and `sort=timestamp` → two of 673 observations, a total count and a next link.
8. `GET /api/v1/readings`, with `district_id=1` → history across that district. Add `start` and `end` using timestamps from your seeded results, e.g. an ISO timestamp with `+00:00`.
9. `GET /api/v1/districts/1/generation-summary` → fresh power and estimated daily energy, including coverage counts.

**Remember:** kW measures power at a moment. kWh measures accumulated energy. Summing cumulative meter totals does not give today's energy.

## 5. Prove the security rules

Log out in Swagger's Authorize dialog before changing credentials.

- Use `user_3_district` (Colombo). Installation 1 should return 200; installation 2 (Gampaha) should return 404. This avoids exposing whether another district's asset exists.
- Use `user_2_province` (Western). Districts 1–3 are visible; district 4 is outside scope.
- Use `installation_1`. Reading provinces should return 403. Submitting to installation 2 should return 403.
- Use a human reader to submit a reading. It should return 403.
- Remove the token. Protected reads should return 401.

All seeded reader/device tokens are long random strings stored as SHA-256 hashes in the database. These are high-entropy API credentials, not user passwords. There is no public registration or token-issuing endpoint.

## 6. Send a meter reading

First, use a reader token to retrieve installation 1's latest reading. Note its `energy_kwh` value. Authorize as `installation_1`, then use `POST /api/v1/installations/1/readings`.

```json
{
  "timestamp": "REPLACE_WITH_CURRENT_ISO_TIMESTAMP_WITH_OFFSET",
  "power_kw": 2.1,
  "energy_kwh": 9999.0,
  "voltage": 230.0
}
```

Replace the timestamp with the current time and energy with a plausible value slightly greater than the last cumulative value. The displayed body is an editing example, not a copy-and-run reading. On a Mac you can obtain the current UTC timestamp with `date -u +%Y-%m-%dT%H:%M:%SZ`.

Expect **201 Created** with a **Location** header. Switch to a reader credential to retrieve that Location. The meter has write permission only. Submitting the same timestamp again returns **409 Conflict**. Updating/deleting an existing reading returns **405 Method Not Allowed**. The database also prevents updates and deletion of readings.

## 7. Run the tests

Open another terminal, activate `.venv`, then run:

```sh
python -m pytest -q
```

Tests use a separate temporary database. They do not modify your demonstration seed. Save the real output as evidence; do not claim checks that you have not run.

## 8. Understand ETag and installation management

An ETag is a fingerprint of a response. Copy an ETag from a GET response and repeat that GET with `If-None-Match: <the-tag>`. Expect **304** and an empty body if the response is unchanged. Swagger may not expose arbitrary headers; use curl or an API client:

```sh
curl -i -H "Authorization: Bearer $READER_TOKEN" \
  -H 'If-None-Match: "PASTE_ETAG_VALUE_HERE"' \
  http://127.0.0.1:8000/api/v1/installations/1
```

`READER_TOKEN` must be set in your local terminal first. Do not put credentials in screenshots or commits.

Provisioning is disabled unless `PROVISIONING_TOKEN` is set before starting the server. Generate a secret with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`, store it privately, and set that environment variable. This is a separate infrastructure credential, not an SLSEA reader or meter.

- POST `/api/v1/installations` creates an empty asset and returns its device token once.
- GET that asset using a national reader to obtain its ETag.
- PUT `/api/v1/installations/{id}` replaces all editable fields and requires `If-Match` with the current ETag. Missing header → 428; stale tag → 412.
- DELETE removes an asset only if it has no readings. Repeating deletion still returns 204. Existing history blocks deletion with 409.

Check this provisioning interpretation against your lecturer's design guidelines, which were not supplied. Do not add update/delete to the append-only history just to demonstrate CRUD.

## 9. Publish and finish the coursework

Follow `docs/DEPLOYMENT.md` for remote Git and HTTPS hosting, then `docs/REPORT_WORKSHEET.md` for writing your own report. Use `docs/VIVA_GUIDE.md` to practise explaining the code.

Your supplied GitHub repository is configured as `origin`; this implementation uses branch `coursework/solar-api`. The existing remote `main` is the Police Tuk-Tuk teaching project. This local coursework branch contains real incremental AI-assisted commits from this build. Continue committing your own changes as you make them; do not invent or backdate history. Review `docs/AI_DISCLOSURE.md`, include the required prompts/references in your appendix, and sign the official declaration yourself.

## File guide

| File | Simple purpose |
|---|---|
| `app/db.py` | Tables, relationships, indexes and immutable-history rules |
| `app/seed.py` | Synthetic geography/assets/history and private credentials |
| `app/main.py` | Routes, authorization, validation, caching and summaries |
| `tests/test_api.py` | Automated examples proving correct behaviour |
| `Dockerfile` | Runs the same service in a hosted container |
| `docs/MODEL.md` | Domain model and explicit assumptions |
| `docs/REPORT_WORKSHEET.md` | Questions to answer yourself with evidence |
| `docs/AI_DISCLOSURE.md` | Honest record of this assistance |
