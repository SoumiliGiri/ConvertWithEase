# ConvertWithEase
A secure file converting website, build with HTML, CSS, JS and python.

## 🚀 About This Project

I built this as a learning project while exploring vibe coding with AI.
The goal was to create a genuinely useful tool that solves a real problem
— converting documents between formats — without the shady practices that
plague most free converter websites.

Starting from zero knowledge of Python and Flask, I used AI assistance to
understand concepts, debug errors, and build features step by step. Every
decision, from the folder structure to the security implementation, was
something I learned along the way.

## Features

- **Convert between formats** — PDF, DOCX, PPTX, XLSX, JPG, PNG and more
- **Instant file deletion** — your file is permanently deleted the moment
  your download starts, not stored on any server
- **No accounts required** — no sign-up, no email, no tracking
- **Rate limiting** — prevents abuse with a 10 requests/minute limit
- **File type scanning** — checks actual file content, not just the extension
- **Clean UI** — drag & drop interface with live progress feedback

## Tech Stack

| Frontend | HTML, CSS, Vanilla JavaScript |
| Backend | Python, Flask |
| File Conversion | LibreOffice (headless), pdf2docx, Pillow |
| Security | flask-limiter, python-magic, CORS |
| Font | Lexend Deca (self-hosted) |

## Screenrecord
[Watch Video](Screenrecord/Recording.mp4)

## Project Structure
```
ConvertWithEase/
│
├── server.py            ← Flask backend
├── requirements.txt     ← Python dependencies
│
└── static/
    ├── index.html       ← Frontend UI
    ├── style.css        ← All styling
    ├── app.js           ← All interactivity
    └── Font/
        └── lexend-deca-v25-latin-regular.woff2
```

## Running Locally

**1. Install system dependencies**
```bash
# Windows — download installer from libreoffice.org
# Then add C:\Program Files\LibreOffice\program to your PATH
```

**2. Install Python packages**
```bash
pip install -r requirements.txt
```

**3. Start the server**
```bash
python server.py
```

**4. Open in browser**
```
http://localhost:5000
```

## Requirements

- Python
- LibreOffice (for Office ↔ PDF conversions)
- pip packages listed in `requirements.txt`

## What I Learned

- How Flask routes and serves files
- How browsers and servers communicate via HTTP requests
- Why `/tmp/` paths don't work on Windows and how to fix it
- How environment variables (PATH) work on Windows
- What rate limiting, CORS, and file type scanning actually do
- How to structure a full-stack project from scratch
