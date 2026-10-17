from app.ai_review.prompts import review_prompt

def test_prompt_treats_repository_content_as_untrusted_and_bounds_patch():
    prompt = review_prompt([{"filename":"x.py", "patch":"a" * 15000}])
    assert "untrusted data" in prompt
    assert len(prompt) < 13000
