"""Curated exercises. Answers and explanations are only returned after submission."""

EXERCISES = [
    {
        "id": "empty-average-1", "title": "Guard an empty collection", "description": "A helper calculates an average from caller-provided values.",
        "language": "python", "difficulty": "beginner", "category": "bug", "instructions": "Which change prevents division by zero while keeping the empty case explicit?",
        "code_snippet": "def average(values: list[float]) -> float:\n    return sum(values) / len(values)",
        "hints": ["The denominator is zero when the collection has no elements."],
        "options": ["Return 0 when values is empty, otherwise calculate the average.", "Catch every Exception around the division.", "Convert values to a tuple before dividing."],
        "learning_objectives": ["Identify an empty-input edge case", "Choose an explicit return contract"],
        "correct_answer": "Return 0 when values is empty, otherwise calculate the average.",
        "explanation": "An explicit empty-input policy prevents division by zero and documents the function's behavior.",
    },
    {
        "id": "shell-input-1", "title": "Avoid shell interpolation", "description": "A program needs to call a local analyzer with a user-selected file path.",
        "language": "python", "difficulty": "intermediate", "category": "security", "instructions": "Which subprocess call avoids interpreting the file path as shell syntax?",
        "code_snippet": "path = request.query_params['path']\n# Run the analyzer on path",
        "hints": ["Prefer argument vectors and keep shell parsing disabled."],
        "options": ["subprocess.run(['analyzer', path], shell=False, check=False)", "subprocess.run(f'analyzer {path}', shell=True)", "eval(path)"],
        "learning_objectives": ["Recognize command injection risk", "Use argument-vector subprocess APIs"],
        "correct_answer": "subprocess.run(['analyzer', path], shell=False, check=False)",
        "explanation": "Passing separate arguments avoids shell interpretation, though the path should still be validated and constrained.",
    },
    {
        "id": "path-traversal-1", "title": "Constrain a repository path", "description": "A review service reads a file named by a pull-request diff.",
        "language": "python", "difficulty": "intermediate", "category": "security", "instructions": "What must be checked before opening the file?",
        "code_snippet": "target = checkout / filename\ntext = target.read_text()",
        "hints": ["A filename may contain parent-directory segments or resolve through a symlink."],
        "options": ["Resolve the target and verify it remains beneath the checkout root.", "Check that the string starts with the checkout path.", "Replace every dot in the filename."],
        "learning_objectives": ["Understand path traversal", "Account for symlinks when checking containment"],
        "correct_answer": "Resolve the target and verify it remains beneath the checkout root.",
        "explanation": "Canonical path resolution followed by a relative-to-root check blocks parent traversal and symlink escapes.",
    },
]
