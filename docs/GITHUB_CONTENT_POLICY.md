# GitHub Content Policy

This private repository is allowed to version a complete application snapshot.

## Commit To GitHub

- Application source code
- Tests, migrations, prompt templates, and documentation
- `data/fashuo.db`
- `data/uploads/`
- `data/documents/`

The `data/` files are treated as user study data. They may be committed only because the repository owner explicitly approved full-project synchronization.

## Never Commit

- `.env`
- API keys or access tokens
- `backups/`
- `logs/`
- Python caches and virtual environments

## Deployment Note

GitHub stores the project and data snapshot, but it does not run this Streamlit application by itself. To make the app available online, deploy from this repository to a Python-capable host such as Streamlit Community Cloud, Render, Railway, or a VPS, and configure API keys through that platform's secret settings.

## Public Release Rule

Before making this repository public, create a scrubbed branch or release package that removes personal study data and uses a sample database instead of the real `data/fashuo.db`.
