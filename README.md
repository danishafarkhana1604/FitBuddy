# FitBuddy – AI Fitness Plan Generator

A complete FastAPI + Jinja2 + SQLAlchemy + SQLite web application based on the supplied FitBuddy project documentation. It generates personalized 7-day workout plans, nutrition/recovery tips, and feedback-based plan revisions.

## Stack

- FastAPI + Uvicorn
- Jinja2 templates
- SQLAlchemy 2.x + SQLite
- Pydantic v2 validation
- Google GenAI Python SDK (`google-genai`)
- Gemini 2.5 Pro for workout generation/update
- Gemini 2.5 Flash for concise nutrition/recovery tips
- Responsive HTML/CSS/JavaScript frontend
- REST API + browser UI

## Important implementation note

The supplied documentation describes the older `google-generativeai` SDK and Gemini 1.5 Pro/Flash. This implementation uses Google's current `google-genai` SDK and current supported Gemini 2.5 model names so the code follows the current Gemini API. The application's feature flow remains the same as the document: 7-day plan, nutrition tip, feedback update, SQLite persistence, and admin view.

## Quick start on Windows

```powershell
cd fitbuddy_project
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and put your Gemini API key in `GEMINI_API_KEY`. For a UI/database-only test, leave the key empty and keep `DEMO_MODE=true`.

Run:

```powershell
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/admin/users

## API examples

### Generate a plan

`POST /api/generate-workout`

```json
{
  "user_id": "FB1001",
  "name": "Arun",
  "age": 21,
  "weight": 70,
  "goal": "muscle gain",
  "intensity": "medium",
  "experience_level": "beginner",
  "days_per_week": 5
}
```

### Submit feedback

`POST /api/feedback`

```json
{
  "user_id": "FB1001",
  "feedback": "Add more cardio and keep Friday as a lighter recovery day."
}
```

## Project structure

```text
fitbuddy_project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── ai_service.py
│   ├── routes.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── result.html
│   │   ├── feedback.html
│   │   ├── all_users.html
│   │   └── error.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Testing

With the virtual environment active:

```powershell
pytest -q
```

The tests use demo mode and do not require a Gemini API key.

## Gemini API key

Create a Gemini API key through Google's Gemini API documentation, then put it in `.env`:

```env
GEMINI_API_KEY=your_key_here
DEMO_MODE=false
```

Do not commit `.env` or expose your API key in frontend JavaScript.
