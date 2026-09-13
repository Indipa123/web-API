# Publish the API step by step

Public deployment has not been performed: you confirmed that you do not yet use a hosting provider. The code has been published to your supplied GitHub repository on branch `coursework/solar-api`. Choose a hosting service/account first. The Render route below uses a paid service and persistent disk; review its current price before you create it. No purchase is included in this project.

## A. Publish to your supplied repository

Repository: https://github.com/Indipa123/web-API.git

Its `main` branch contains the Police Tuk-Tuk teaching project. The solar implementation is prepared on the separate `coursework/solar-api` branch, with its own genuine build history. Keep the taught reference project out of your solar deliverable. Select the coursework branch when viewing code, deploying and giving the marker a repository URL.

The local project already has the correct `origin` remote. From inside the project, run:

```sh
git remote -v
git log --oneline
git push -u origin coursework/solar-api
```

If authentication is required, sign in through your normal Git tooling or GitHub Desktop; do not send tokens in chat or store them in code. No force push is needed. See `VERIFICATION.md` for whether the assistant's push attempt succeeded.

Invite the module leader through repository settings using their confirmed Git hosting username. The email in the brief does not identify a confirmed GitHub username. This invitation remains your action.

For every real later improvement, commit the changed files with an accurate message and push. Do not invent a history or change the AI-generated commits to claim unaided authorship.

## B. Deploy using Render Docker

1. Create a Render account at https://render.com and connect your GitHub account. Create a new Web Service, select `Indipa123/web-API`, and select branch `coursework/solar-api`.
2. Select **Docker** as the language/runtime. Use the supplied root `Dockerfile`.
3. Select an appropriate paid service and attach a persistent disk mounted at `/var/data` (1 GB is ample for the demonstration seed; check your actual usage).
4. Add environment variables:

| Variable | Value |
|---|---|
| `DATABASE_PATH` | `/var/data/solar.db` |
| `CREDENTIALS_PATH` | `/var/data/credentials.json` |
| `AUTO_SEED` | `true` |
| `PROVISIONING_TOKEN` | A new private random secret, only if management is needed |

5. Set the health-check path to `/health`. Deploy.
6. The start command initializes/seeds at runtime, when the disk is mounted. On later starts, the seed detects existing data and preserves it. The application uses the host's `PORT` variable, defaulting to 8000.
7. Open your assigned HTTPS address followed by `/health`, `/docs` and `/openapi.json`.
8. In the service's private shell, read `/var/data/credentials.json` to obtain demonstration credentials. Do not print them in public logs or commit them. Give the marker only the needed test credentials through the course's private submission channel.
9. Repeat the README's read, write and authorization checks against the HTTPS service. Record real status codes and headers.
10. Restart the service and confirm your newly ingested reading survives. This verifies persistent storage, rather than only verifying initial seed data.

Render documents Docker deployment and persistent storage here:
- https://render.com/docs/docker
- https://render.com/docs/disks

Render's normal filesystem is ephemeral: without the mounted disk, new data can disappear on redeployment. Its persistent disks are available for paid services and bind this design to one service instance. Read the provider's current conditions before deployment.

## C. Optional local Docker check

```sh
docker build -t solar-api .
docker run --rm -p 8000:8000 -e AUTO_SEED=true \
  -e DATABASE_PATH=/var/data/solar.db \
  -e CREDENTIALS_PATH=/var/data/credentials.json \
  -v solar-data:/var/data solar-api
```

The `solar-data` volume preserves data between container runs. Swagger is then at `http://127.0.0.1:8000/docs`. Local Docker is a rehearsal; it does not satisfy the public HTTPS requirement.

FastAPI's container guidance: https://fastapi.tiangolo.com/deployment/docker/

## D. Capture evidence

Record the actual deployment URL, time/date, commit hash (`git rev-parse HEAD`), health result, Swagger screenshot, successful POST with Location, denied out-of-scope read, paginated history and 304 response. Redact tokens. Do not fabricate deployment screenshots or test results.

Keep the service operational for marking. For this SQLite design, use one service instance and one worker. A full national service would require a different storage/scaling architecture and operational controls.
