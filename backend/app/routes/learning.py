"""Persistent, server-authored learning exercises and progress endpoints."""

from fastapi import APIRouter, HTTPException

from app.data.learning_exercises import EXERCISES
from app.database.reviews import get_store
from app.schemas.learning import AnswerRequest, LearningExercise

router = APIRouter(prefix="/api/learning", tags=["learning"])


def _exercise(item: dict) -> dict:
    return LearningExercise.model_validate({key: value for key, value in item.items() if key not in {"correct_answer", "explanation"}}).model_dump()


@router.get("/exercises", response_model=list[LearningExercise])
def list_exercises(difficulty: str | None = None):
    return [_exercise(item) for item in EXERCISES if difficulty is None or item["difficulty"] == difficulty]


@router.get("/exercises/{exercise_id}", response_model=LearningExercise)
def get_exercise(exercise_id: str):
    item = next((item for item in EXERCISES if item["id"] == exercise_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Learning exercise not found.")
    return _exercise(item)


@router.post("/exercises/{exercise_id}/submit")
def submit_exercise(exercise_id: str, payload: AnswerRequest):
    item = next((item for item in EXERCISES if item["id"] == exercise_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Learning exercise not found.")
    correct = payload.answer.strip().casefold() == item["correct_answer"].casefold()
    try:
        store = get_store()
        store.record_learning_attempt(exercise_id, item["category"], correct)
        progress = store.learning_progress()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Learning progress could not be saved.") from exc
    return {"correct": correct, "explanation": item["explanation"], "feedback": "Correct — well reasoned." if correct else "Not quite. Review the hint and try again.", "points": 10 if correct else 0, "progress": progress}


@router.get("/progress")
def learning_progress():
    try:
        return get_store().learning_progress()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Learning progress is unavailable.") from exc


@router.get("/history")
def learning_history():
    try:
        return get_store().learning_history()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Learning history is unavailable.") from exc
