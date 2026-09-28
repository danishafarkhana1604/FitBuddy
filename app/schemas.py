from typing import Literal

from pydantic import BaseModel, Field, field_validator


Goal = Literal["weight loss", "muscle gain", "general wellness", "flexibility", "endurance"]
Intensity = Literal["low", "medium", "high"]
ExperienceLevel = Literal["beginner", "intermediate", "advanced"]


class UserInput(BaseModel):
    user_id: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=13, le=100)
    weight: float = Field(gt=20, le=300)
    goal: Goal
    intensity: Intensity
    experience_level: ExperienceLevel = "beginner"
    days_per_week: int = Field(ge=2, le=7)

    @field_validator("user_id", "name")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=50)
    feedback: str = Field(min_length=5, max_length=2000)


class GenerateResponse(BaseModel):
    message: str
    user_id: str
    workout_plan: str
    nutrition_tip: str


class FeedbackResponse(BaseModel):
    message: str
    user_id: str
    updated_plan: str
