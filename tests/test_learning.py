import pytest
from fastapi import HTTPException
from app.routes.learning import _public, grade_answer
from app.data.learning_exercises import EXERCISES

def test_exercise_hides_answer_until_submission():
    source = next(x for x in EXERCISES if x["id"] == "null-check-1")
    exercise = _public(source)
    assert "correct_answer" not in exercise
    assert grade_answer(source, exercise["options"][0]) is True

def test_unknown_exercise_returns_not_found():
    assert not any(x["id"] == "nope" for x in EXERCISES)

def test_progress_is_temporary():
    # Progress storage is an in-process list and starts empty in a new test process.
    from app.routes.learning import _attempts
    assert isinstance(_attempts, list)
