from collections import Counter
from threading import RLock
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.data.learning_exercises import EXERCISES

router = APIRouter(prefix="/api/learning", tags=["learning"])
_attempts: list[dict] = []
_lock = RLock()

class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)

def _public(item):
    return {key:value for key,value in item.items() if key not in {"correct_answer", "explanation"}}

def grade_answer(item: dict, answer: str) -> bool:
    return answer.strip().casefold() == item["correct_answer"].casefold()

@router.get("/exercises")
async def list_exercises(difficulty: str | None = None):
    items = [item for item in EXERCISES if not difficulty or item["difficulty"] == difficulty]
    return [_public(item) for item in items]

@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    item = next((item for item in EXERCISES if item["id"] == exercise_id), None)
    if not item: raise HTTPException(404, "Exercise not found.")
    return _public(item)

@router.post("/exercises/{exercise_id}/submit")
async def submit(exercise_id: str, payload: AnswerRequest):
    item = next((item for item in EXERCISES if item["id"] == exercise_id), None)
    if not item: raise HTTPException(404, "Exercise not found.")
    correct = grade_answer(item, payload.answer)
    attempt = {"exercise_id":exercise_id,"category":item["category"],"correct":correct}
    with _lock: _attempts.append(attempt)
    return {"correct":correct,"explanation":item["explanation"],"feedback":"Correct — well reasoned." if correct else "Not quite. Review the hint and try to identify the unsafe assumption.","points":10 if correct else 0,"progress":progress()}

@router.get("/progress")
async def progress():
    with _lock: attempts = list(_attempts)
    return {"temporary":True,"exercises_completed":len(attempts),"correct_answers":sum(x["correct"] for x in attempts),"attempt_count":len(attempts),"accuracy":(sum(x["correct"] for x in attempts)/len(attempts) if attempts else 0),"topics_practiced":dict(Counter(x["category"] for x in attempts))}

@router.get("/history")
async def history():
    with _lock: return {"temporary":True,"attempts":list(reversed(_attempts[-100:]))}
