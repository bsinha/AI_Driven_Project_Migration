# Deploy MATE (Context Atlas UI) on Streamlit Community Cloud

Public hosting uses **[Streamlit Community Cloud](https://share.streamlit.io/)** (free tier: apps at `*.streamlit.app`).

## Prerequisites

1. GitHub repo with this project pushed (e.g. `feature/visual-pipeline-ux` or `main`).
2. GitHub account authorized at [share.streamlit.io](https://share.streamlit.io/).

## One-time setup in the repo (already added)

| File | Purpose |
|------|---------|
| `requirements.txt` (repo root) | Installs `platform` package (`-e ./platform`) |
| `.streamlit/config.toml` (repo root) | Required by Community Cloud (single config at root) |
| `.python-version` | Python 3.11 |
| `.streamlit/secrets.toml.example` | Template for secrets in the Cloud UI |

## Deploy from the Streamlit UI (Deploy button)

1. Run locally: `cd platform` → `streamlit run migrate_framework/ui/app.py`
2. Click **Deploy** (top-right) → **Deploy to Streamlit Community Cloud**.
3. Sign in with GitHub if prompted.
4. On [share.streamlit.io](https://share.streamlit.io/), **Create app** and set:

   | Field | Value |
   |-------|--------|
   | Repository | Your fork/org repo |
   | Branch | `main` or your feature branch |
   | Main file path | `platform/migrate_framework/ui/app.py` |

5. **Advanced settings** (optional): Python 3.11 if not picked from `.python-version`.

6. **Secrets** (App settings → Secrets) — paste (optional, for LLM stages):

   ```toml
   OPENAI_API_KEY = "sk-..."
   ```

7. **Save** → Cloud builds and publishes `https://<your-app>.streamlit.app`.

## Deploy from share.streamlit.io directly

1. [Create app](https://share.streamlit.io/deploy) → **Yup, I have an app**.
2. Same **Main file path**: `platform/migrate_framework/ui/app.py`.
3. Wait for the build log; fix missing deps by updating `platform/pyproject.toml` / root `requirements.txt`.

## After deploy — first use

1. Open the public URL.
2. Sidebar → **Active project** → **— new —**.
3. Defaults should point at `sample-bank` (repo-relative). Click **Initialize project**.
4. Run pipeline stages (or use a pre-built project if you commit one under `platform/projects/`).

**Note:** `platform/projects/` is gitignored by default. Cloud starts with no saved projects until someone initializes one.

## Local vs Cloud paths

- Community Cloud runs with **working directory = repository root**.
- Init form uses `_default_sample_bank_paths()` so `sample-bank/` resolves correctly on Cloud.
- For local dev from `platform/`, LAN binding still uses `platform/.streamlit/config.toml`.

## Security

- Community Cloud apps are **public** unless you use Streamlit's access controls on paid plans.
- Do not commit `.env` or real API keys; use Cloud **Secrets** only.
- This POC has **no in-app authentication** — treat as a demo environment.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: migrate_framework` | Ensure root `requirements.txt` contains `-e ./platform` |
| Logo missing | Package data includes `ui/assets`; rebuild after package changes |
| OpenAI stages fail | Add `OPENAI_API_KEY` in Cloud secrets |
| Build uses wrong Python | Set `.python-version` to `3.11` |
