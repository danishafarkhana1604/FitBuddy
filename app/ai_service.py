from __future__ import annotations

import re
from typing import Any

from .config import get_settings
from .schemas import UserInput

settings = get_settings()

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - dependency is installed from requirements.txt
    genai = None
    types = None


class AIServiceError(RuntimeError):
    """Raised when an AI request cannot be completed."""


def _client():
    if not settings.gemini_api_key:
        raise AIServiceError(
            "GEMINI_API_KEY is not configured. Add it to .env or enable DEMO_MODE=true."
        )
    if genai is None:
        raise AIServiceError("The google-genai package is not installed. Run pip install -r requirements.txt.")
    return genai.Client(api_key=settings.gemini_api_key)


def _clean_model_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:text|markdown)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _demo_plan(user: UserInput) -> str:
    sessions = {
        "weight loss": [
            ("Full Body + Cardio", "Bodyweight squats 3x12; incline push-ups 3x10; reverse lunges 3x10/side; brisk walk 20 min"),
            ("Cardio + Core", "Brisk walk 25 min; dead bugs 3x10/side; plank 3x30 sec; mountain climbers 3x20"),
            ("Lower Body", "Squats 3x12; glute bridges 3x15; step-ups 3x10/side; easy cycling 15 min"),
            ("Active Recovery", "Easy walk 25 min; mobility 15 min; gentle stretching 10 min"),
            ("Upper Body + Cardio", "Incline push-ups 3x10; backpack rows 3x12; shoulder taps 3x20; brisk walk 20 min"),
            ("Full Body Circuit", "Squats 3x12; rows 3x12; lunges 3x10/side; jumping jacks 3x30 sec"),
            ("Recovery", "Easy walk 20 min; full-body mobility 15 min; breathing 5 min"),
        ],
        "muscle gain": [
            ("Upper Body", "Push-ups 3x8-12; rows 4x8-12; shoulder press 3x10; curls 3x12"),
            ("Lower Body", "Squats 4x8-12; Romanian deadlift 3x10; lunges 3x10/side; calf raises 3x15"),
            ("Recovery", "Easy walk 20 min; hip/shoulder mobility 15 min; light stretching"),
            ("Upper Body", "Incline press 3x10; rows 4x10; lateral raises 3x12; triceps extensions 3x12"),
            ("Lower Body + Core", "Goblet squats 4x10; hip thrusts 4x10; split squats 3x8/side; plank 3x40 sec"),
            ("Full Body", "Squats 3x10; push-ups 3x10; rows 3x10; hip hinge 3x10"),
            ("Rest", "Complete rest or a gentle 15-20 minute walk and mobility work"),
        ],
    }
    default = [
        ("Full Body", "Squats 3x10; incline push-ups 3x10; rows 3x10; plank 3x30 sec"),
        ("Cardio", "Brisk walk 25 min; mobility 10 min; breathing 5 min"),
        ("Lower Body", "Squats 3x12; glute bridges 3x15; step-ups 3x10/side"),
        ("Recovery", "Easy walk 20 min; gentle mobility 15 min"),
        ("Upper Body", "Incline push-ups 3x10; rows 3x12; shoulder taps 3x20"),
        ("Flexibility", "Dynamic warm-up 5 min; yoga-style mobility 25 min; breathing 5 min"),
        ("Rest", "Rest and light movement only"),
    ]
    selected = sessions.get(user.goal, default)
    lines = [
        "FITBUDDY — 7-DAY PERSONALIZED WORKOUT PLAN",
        f"Goal: {user.goal.title()} | Intensity: {user.intensity.title()} | Experience: {user.experience_level.title()}",
        f"Suggested schedule: {user.days_per_week} training days/week",
        "",
    ]
    for day, (focus, workout) in enumerate(selected, 1):
        if day > user.days_per_week:
            focus = "Recovery / Optional Movement"
            workout = "Easy walk 15-20 min, mobility, and rest as needed."
        lines.extend([
            f"DAY {day} — {focus}",
            "Warm-up (5-10 min): Easy movement + dynamic mobility.",
            f"Main workout: {workout}.",
            "Rest: 60-90 sec between strength sets unless otherwise comfortable.",
            "Cooldown: 5-10 min gentle stretching and relaxed breathing.",
            "",
        ])
    lines.extend([
        "SAFETY NOTE",
        "Use controlled form, adjust load/repetitions to your ability, and stop if you experience sharp pain, dizziness, or unusual symptoms. Consider professional guidance for medical or injury-related concerns.",
    ])
    return "\n".join(lines)


def _demo_tip(goal: str) -> str:
    tips = {
        "weight loss": "Build meals around vegetables, a protein source, whole-food carbohydrates, and adequate water. Consistent habits matter more than extreme restriction.",
        "muscle gain": "Include a protein-rich food in each main meal and eat enough overall energy to support training and recovery. Good options include eggs, fish, chicken, beans, tofu, or Greek yogurt.",
        "general wellness": "Prioritize regular meals, hydration, fruits and vegetables, adequate protein, and consistent sleep to support everyday energy and recovery.",
        "flexibility": "Stay hydrated and include protein-rich foods plus a varied diet. Recovery from mobility work also benefits from adequate sleep and regular meals.",
        "endurance": "Hydrate consistently and include carbohydrate-rich whole foods around longer sessions, alongside adequate protein for recovery.",
    }
    return tips.get(goal, tips["general wellness"])


def generate_workout(user: UserInput) -> str:
    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_plan(user)

    prompt = f"""
You are FitBuddy, a fitness-planning assistant. Create a safe, practical, personalized 7-day
workout plan for the following user:
- Name: {user.name}
- Age: {user.age}
- Weight: {user.weight} kg
- Goal: {user.goal}
- Intensity: {user.intensity}
- Experience level: {user.experience_level}
- Training days per week: {user.days_per_week}

Requirements:
1. Produce exactly 7 day sections.
2. Respect the requested number of training days and use recovery/rest days for the remaining days.
3. Every training day must contain warm-up (5-10 min), main workout, sets/reps or duration, rest guidance,
   and cooldown/recovery guidance.
4. Keep exercise selection appropriate to the experience level and intensity.
5. Include variety across full body, upper/lower body, cardio, core, mobility, and recovery where appropriate.
6. Do not prescribe medical treatment or claim to diagnose conditions.
7. Do not recommend dangerous training practices or extreme dieting.
8. Return plain text with clear headings; do not wrap the answer in Markdown code fences.
"""
    try:
        client = _client()
        response = client.models.generate_content(
            model=settings.gemini_workout_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=3500,
            ),
        )
        text = _clean_model_text(response.text)
        if not text:
            raise AIServiceError("Gemini returned an empty workout plan.")
        return text
    except Exception as exc:
        raise AIServiceError(f"Workout generation failed: {exc}") from exc


def generate_nutrition_tip(goal: str) -> str:
    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_tip(goal)

    prompt = f"""
Give one concise, practical nutrition or recovery tip for a person whose fitness goal is: {goal}.
Keep it to 2-4 sentences. Focus on balanced eating, hydration, protein/carbohydrates as appropriate,
recovery, or sustainable habits. Avoid individualized medical advice, extreme calorie restriction,
and unsupported claims. Return plain text only.
"""
    try:
        client = _client()
        response = client.models.generate_content(
            model=settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=300,
            ),
        )
        text = _clean_model_text(response.text)
        if not text:
            raise AIServiceError("Gemini returned an empty nutrition tip.")
        return text
    except Exception as exc:
        raise AIServiceError(f"Nutrition tip generation failed: {exc}") from exc


def update_workout_plan(original_plan: str, feedback: str, user: UserInput) -> str:
    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_update(original_plan, feedback, user)

    prompt = f"""
You are revising a FitBuddy 7-day workout plan.

User profile:
- Age: {user.age}
- Weight: {user.weight} kg
- Goal: {user.goal}
- Intensity: {user.intensity}
- Experience: {user.experience_level}
- Training days/week: {user.days_per_week}

Original plan:
{original_plan}

User feedback:
{feedback}

Create a revised 7-day plan that addresses the feedback while preserving useful parts of the original.
Keep the same safety requirements: warm-up, main workout with sets/reps or duration, rest guidance,
cooldown/recovery, appropriate intensity, and no medical diagnosis or extreme dieting.
Return plain text with clear headings and no code fences.
"""
    try:
        client = _client()
        response = client.models.generate_content(
            model=settings.gemini_workout_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=3500,
            ),
        )
        text = _clean_model_text(response.text)
        if not text:
            raise AIServiceError("Gemini returned an empty updated plan.")
        return text
    except Exception as exc:
        raise AIServiceError(f"Plan update failed: {exc}") from exc


def _demo_update(original_plan: str, feedback: str, user: UserInput) -> str:
    # Keep the demo mode deterministic while visibly incorporating feedback.
    return (
        f"{original_plan}\n\n"
        "UPDATED USING FEEDBACK\n"
        f"Requested changes: {feedback}\n"
        "The demo version keeps the original structure and marks the requested adjustment for testing. "
        "When GEMINI_API_KEY is configured and DEMO_MODE=false, Gemini will regenerate the complete plan."
    )
