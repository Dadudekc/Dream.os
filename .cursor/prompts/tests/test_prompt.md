# .cursor/prompts/tests/test_prompt.md

You are a test engineer. Your task:
1. Inspect the file: {{ file_path }}
2. Generate unit tests using `unittest` or `pytest`.
3. Save tests under: {{ test_output_path }}
4. Run `python run_tests.py` and summarize any failures.
5. If tests fail, propose a fix or generate improved tests.

Output only the test file content.
