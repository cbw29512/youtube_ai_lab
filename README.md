# YouTube AI Lab

YouTube AI Lab is an experimental local-AI content pipeline exploring how viewer feedback can influence generated video concepts and production workflows.

The project combines local language models, text-to-speech, Python automation, video tooling, and a lightweight dashboard. It is a lab/portfolio project, not a hosted production service.

## Stack

- Local AI: Ollama
- Text to speech: Piper
- Backend: Python / Flask
- Video processing: FFmpeg
- Storage: SQLite

## Quick start

Create and activate a Python virtual environment, install the project requirements, then start the Flask backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/app.py
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python backend/app.py
```

Use the local address reported by Flask rather than relying on machine-specific IP addresses from another installation.

## Public-release status

**Experimental / active development.** The repository is suitable as a portfolio and learning project, but it is not yet production-certified.

Before a public hosted release, the project should have:

- automated tests and CI
- dependency and secret scanning
- portable environment configuration
- explicit handling for generated-media storage
- rate/resource limits for AI and video jobs
- copyright/platform-policy review for generated or source media
- accessibility and mobile checks for the dashboard
- documented cleanup/recovery behavior

## Privacy and safety

Do not commit API keys, private channel credentials, unpublished media, viewer personal information, or machine-specific secrets. Keep local model endpoints and internal network details configurable through environment variables rather than hard-coded documentation.

Generated content should be reviewed before publication. Do not treat model output as automatically accurate, original, safe to publish, or compliant with a platform's policies.

## Support

If YouTube AI Lab is useful as a learning or experimentation project, you can support continued development here:

**Buy Me a Coffee:** https://buymeacoffee.com/divclass016
