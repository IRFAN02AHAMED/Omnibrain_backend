# OmniBrain Backend Merge Notes

This zip is your OmniBrain backend merged with the Jira + GitHub connector logic from `Jira_Git.zip`.

## What was merged

- Added Jira connector routes and services.
- Added GitHub connector routes and services.
- Added `app/core/oauth_state.py` for safe OAuth state handling.
- Extended `app/core/config.py` with Atlassian/GitHub OAuth settings.
- Extended `app/repositories/connected_account_repository.py` so Jira/GitHub use your existing `connected_accounts` table.
- Registered Jira/GitHub routers in `main.py`.

## Important design choice

Your project keeps **one common connector table**:

`connected_accounts`

It does **not** use your friend's separate `connector_connections` table.

Provider-specific fields are stored in `connected_accounts.metadata`:

- Jira: `cloud_id`, `site_url`, `site_name`
- GitHub: `github_username`
- Google: Drive folder IDs

## New endpoints

Jira:

- `GET /connectors/jira/connect?token=YOUR_JWT`
- `GET /connectors/jira/callback`
- `GET /connectors/jira/status`
- `GET /connectors/jira/projects`

GitHub:

- `GET /connectors/github/connect?token=YOUR_JWT`
- `GET /connectors/github/callback`
- `GET /connectors/github/status`
- `GET /connectors/github/repos`

## Setup reminders

Copy `.env.example` to `.env` and fill your real values.

Add these callback URLs in provider consoles:

- Atlassian/Jira: `http://localhost:8000/connectors/jira/callback`
- GitHub OAuth App: `http://localhost:8000/connectors/github/callback`

Run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing flow

1. Login with your app and get a JWT.
2. Open in browser:
   - `http://localhost:8000/connectors/jira/connect?token=YOUR_JWT`
   - `http://localhost:8000/connectors/github/connect?token=YOUR_JWT`
3. After connecting, use Swagger with `Authorization: Bearer YOUR_JWT`.
4. Test:
   - `/connectors/jira/status`
   - `/connectors/jira/projects`
   - `/connectors/github/status`
   - `/connectors/github/repos`
