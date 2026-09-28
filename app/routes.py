from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai_service import AIServiceError, generate_nutrition_tip, generate_workout, update_workout_plan
from .config import get_settings
from .database import get_db
from .models import User, WorkoutPlan
from .schemas import FeedbackRequest, FeedbackResponse, GenerateResponse, UserInput

settings = get_settings()
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _user_from_form(
    user_id: str,
    name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    experience_level: str,
    days_per_week: int,
) -> UserInput:
    return UserInput(
        user_id=user_id,
        name=name,
        age=age,
        weight=weight,
        goal=goal,
        intensity=intensity,
        experience_level=experience_level,
        days_per_week=days_per_week,
    )


def _get_user_by_public_id(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.user_id == user_id))


def _result_context(request: Request, user: User, plan: WorkoutPlan) -> dict:
    return {
        "request": request,
        "user": user,
        "plan": plan,
        "page_title": "Your Personalized Plan",
        "demo_mode": settings.demo_mode or not settings.gemini_api_key,
    }


@router.get("/", response_class=HTMLResponse, name="home")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"page_title": "AI Workout Generator", "demo_mode": settings.demo_mode or not settings.gemini_api_key},
    )


@router.post("/generate-workout", response_class=HTMLResponse, name="generate_workout_page")
def generate_workout_page(
    request: Request,
    user_id: Annotated[str, Form()],
    name: Annotated[str, Form()],
    age: Annotated[int, Form()],
    weight: Annotated[float, Form()],
    goal: Annotated[str, Form()],
    intensity: Annotated[str, Form()],
    experience_level: Annotated[str, Form()],
    days_per_week: Annotated[int, Form()],
    db: Session = Depends(get_db),
):
    try:
        user_data = _user_from_form(user_id, name, age, weight, goal, intensity, experience_level, days_per_week)
        workout = generate_workout(user_data)
        tip = generate_nutrition_tip(user_data.goal)
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"page_title": "Generation Error", "error": str(exc)},
            status_code=500,
        )

    user = _get_user_by_public_id(db, user_data.user_id)
    if user is None:
        user = User(**user_data.model_dump())
        db.add(user)
        db.flush()
    else:
        for field, value in user_data.model_dump().items():
            setattr(user, field, value)

    plan = user.plan
    if plan is None:
        plan = WorkoutPlan(
            user_id=user.id,
            original_plan=workout,
            nutrition_tip=tip,
        )
        db.add(plan)
    else:
        plan.original_plan = workout
        plan.updated_plan = None
        plan.feedback = None
        plan.nutrition_tip = tip
        plan.updated_at = None
    db.commit()
    db.refresh(user)
    db.refresh(plan)

    return templates.TemplateResponse(request=request, name="result.html", context=_result_context(request, user, plan))


@router.get("/feedback", response_class=HTMLResponse, name="feedback_page")
def feedback_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="feedback.html",
        context={"page_title": "Update Your Plan", "demo_mode": settings.demo_mode or not settings.gemini_api_key},
    )


@router.post("/submit-feedback", response_class=HTMLResponse, name="submit_feedback_page")
def submit_feedback_page(
    request: Request,
    user_id: Annotated[str, Form()],
    feedback: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    try:
        request_data = FeedbackRequest(user_id=user_id, feedback=feedback)
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"page_title": "Invalid Feedback", "error": str(exc)},
            status_code=422,
        )

    user = _get_user_by_public_id(db, request_data.user_id)
    if user is None or user.plan is None:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"page_title": "User Not Found", "error": "No workout plan exists for that User ID."},
            status_code=404,
        )

    user_data = UserInput(
        user_id=user.user_id,
        name=user.name,
        age=user.age,
        weight=user.weight,
        goal=user.goal,
        intensity=user.intensity,
        experience_level=user.experience_level,
        days_per_week=user.days_per_week,
    )
    try:
        updated = update_workout_plan(user.plan.original_plan, request_data.feedback, user_data)
        user.plan.updated_plan = updated
        user.plan.feedback = request_data.feedback
        user.plan.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
        db.refresh(user)
    except AIServiceError as exc:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"page_title": "AI Update Error", "error": str(exc)},
            status_code=500,
        )

    return templates.TemplateResponse(request=request, name="result.html", context=_result_context(request, user, user.plan))


@router.get("/admin/users", response_class=HTMLResponse, name="admin_users")
def admin_users(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={"request": request, "users": users, "page_title": settings.admin_title},
    )


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_user")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = _get_user_by_public_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "ai_mode": "demo" if settings.demo_mode or not settings.gemini_api_key else "gemini",
    }


@router.post("/api/generate-workout", response_model=GenerateResponse)
def api_generate_workout(payload: UserInput, db: Session = Depends(get_db)):
    try:
        workout = generate_workout(payload)
        tip = generate_nutrition_tip(payload.goal)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    user = _get_user_by_public_id(db, payload.user_id)
    if user is None:
        user = User(**payload.model_dump())
        db.add(user)
        db.flush()
    else:
        for field, value in payload.model_dump().items():
            setattr(user, field, value)

    plan = user.plan
    if plan is None:
        plan = WorkoutPlan(user_id=user.id, original_plan=workout, nutrition_tip=tip)
        db.add(plan)
    else:
        plan.original_plan = workout
        plan.updated_plan = None
        plan.feedback = None
        plan.nutrition_tip = tip
        plan.updated_at = None
    db.commit()
    return GenerateResponse(message="Workout plan generated successfully.", user_id=user.user_id, workout_plan=workout, nutrition_tip=tip)


@router.post("/api/feedback", response_model=FeedbackResponse)
def api_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    user = _get_user_by_public_id(db, payload.user_id)
    if user is None or user.plan is None:
        raise HTTPException(status_code=404, detail="No workout plan found for this User ID.")

    user_data = UserInput(
        user_id=user.user_id,
        name=user.name,
        age=user.age,
        weight=user.weight,
        goal=user.goal,
        intensity=user.intensity,
        experience_level=user.experience_level,
        days_per_week=user.days_per_week,
    )
    try:
        updated = update_workout_plan(user.plan.original_plan, payload.feedback, user_data)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    user.plan.updated_plan = updated
    user.plan.feedback = payload.feedback
    from datetime import datetime, timezone
    user.plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    return FeedbackResponse(message="Plan updated successfully.", user_id=user.user_id, updated_plan=updated)


@router.get("/api/users")
def api_users(db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "experience_level": user.experience_level,
            "days_per_week": user.days_per_week,
            "created_at": user.created_at,
            "original_plan": user.plan.original_plan if user.plan else None,
            "updated_plan": user.plan.updated_plan if user.plan else None,
            "feedback": user.plan.feedback if user.plan else None,
        }
        for user in users
    ]
