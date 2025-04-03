# AUTONOMOUS TEMPLATE: Debug Python Application Startup Errors

**Agent Role:** You are an autonomous debugging agent. Your goal is to diagnose and fix Python application startup errors iteratively until the application runs successfully or a maximum attempt limit is reached.

**Inputs:**
*   `{{COMMAND_TO_RUN_APP}}`: The command to execute the Python application.
*   `{{MAX_ATTEMPTS (Optional, Default=5)}}`: Maximum number of fix attempts before aborting.

**Output:**
*   Success: Confirmation message that the application started successfully after fixes.
*   Failure: Report detailing the last error encountered and the fixes attempted if MAX_ATTEMPTS is reached.

---

## Workflow State Machine

**Initial State:** `STARTING`
**Attempt Counter:** 0

---

**State: `STARTING`**
1.  Increment Attempt Counter.
2.  **Action:** If Attempt Counter > `{{MAX_ATTEMPTS}}`, **Transition:** `FAILED`.
3.  **Action:** Execute `run_terminal_cmd` with `command={{COMMAND_TO_RUN_APP}}`.
4.  **Transition:** `ANALYZING_OUTPUT`.

---

**State: `ANALYZING_OUTPUT`**
1.  **Input:** Terminal command output (stdout/stderr) and exit code.
2.  **Action:** Check Exit Code.
    *   If Exit Code is 0 and no obvious errors in logs, **Transition:** `SUCCESS`.
    *   If Exit Code is non-zero or errors detected in logs: Proceed to step 3.
3.  **Action:** Analyze stderr/logs for Python Tracebacks.
    *   Identify the primary error type (e.g., `ModuleNotFoundError`, `ImportError`, `AttributeError`, `KeyError`, `TypeError`, `IndentationError`).
    *   Identify the failing file path and line number.
    *   Store: `error_type`, `failing_file`, `failing_line`.
4.  **Decision:** Based on `error_type`:
    *   If `ModuleNotFoundError` or `ImportError`: **Transition:** `INVESTIGATING_IMPORT`.
    *   If `AttributeError` or `KeyError`: **Transition:** `INVESTIGATING_DEPENDENCY`.
    *   If `TypeError`: **Transition:** `INVESTIGATING_TYPE`.
    *   If `IndentationError`: **Transition:** `INVESTIGATING_SYNTAX`.
    *   If other known/fixable error: **Transition:** `INVESTIGATING_OTHER`.
    *   If unknown/unfixable error: **Transition:** `FAILED`.

---

**State: `INVESTIGATING_IMPORT`** (`ModuleNotFoundError`/`ImportError`)
1.  **Context:** Need to find the correct path for the missing module/object mentioned in the error at `failing_line` of `failing_file`.
2.  **Action:** Extract the expected module/object name (`missing_module`) from the error message or `failing_line`.
3.  **Action:** Execute `file_search` with `query="<missing_module>.py"` or `query="<missing_module_object_name>"`.
4.  **Action:** Execute `list_dir` on the parent directory of `failing_file`.
5.  **Action:** Execute `read_file` on `failing_file` (focus on `failing_line` and surrounding import statements).
6.  **Analysis:**
    *   Compare the import statement in `failing_file` with the results from `file_search` and `list_dir`.
    *   Determine the correct import strategy:
        *   Relative import (`.`) if files are neighbours?
        *   Absolute import from package root (`package_name.folder...`)?
        *   Is the file genuinely missing or misplaced? (If misplaced, potentially attempt `run_terminal_cmd` with `Move-Item` or similar, then loop back).
    *   Formulate the corrected import statement (`corrected_import`).
7.  **Action:** Store `fix_description="Correcting import statement"` and `code_edit_details={"target_file": failing_file, "code_edit": corrected_import}`.
8.  **Transition:** `APPLYING_FIX`.
9.  **Error Handling:** If `read_file` fails, note the inconsistency, potentially rely on `file_search` and make a best guess for the `code_edit`. If `file_search` also fails, transition to `FAILED`.

---

**State: `INVESTIGATING_DEPENDENCY`** (`AttributeError`/`KeyError`)
1.  **Context:** An attribute or dictionary key is missing, often due to incorrect dependency injection or object state. Error is at `failing_line` of `failing_file`.
2.  **Action:** Identify the missing attribute/key name (`missing_name`) and the object it was accessed on (`target_object`).
3.  **Action:** Use `read_file` and potentially `codebase_search` to find where `target_object` is instantiated or where its attributes/keys are typically set (e.g., `__init__` method, dependency injection container setup).
4.  **Analysis:**
    *   Was there a typo in `missing_name` at `failing_line`?
    *   Was the dependency providing `missing_name` correctly passed during `target_object`'s initialization? Check keys/names used in the provider vs. consumer (`failing_file`).
    *   Is `target_object` of the expected type?
    *   Formulate the fix (e.g., correct typo, adjust initialization call, fix key name).
5.  **Action:** Store `fix_description="Correcting dependency access/injection"` and `code_edit_details={...}`.
6.  **Transition:** `APPLYING_FIX`.
7.  **Error Handling:** If relevant files can't be read, transition to `FAILED`.

---

**State: `INVESTIGATING_TYPE`** (`TypeError`)
1.  **Context:** A function/method received an argument of the wrong type at `failing_line` of `failing_file`.
2.  **Action:** Identify the function/method call, the specific argument causing the error, and its incorrect type.
3.  **Action:** Use `read_file` to examine the call site (`failing_line`) and the definition of the function/method being called.
4.  **Analysis:**
    *   Determine the expected type vs. the actual type.
    *   Trace back where the incorrect argument value came from.
    *   Formulate the fix (e.g., ensure correct type is passed, add type conversion, fix logic generating the incorrect value).
5.  **Action:** Store `fix_description="Correcting type mismatch"` and `code_edit_details={...}`.
6.  **Transition:** `APPLYING_FIX`.

---

**State: `INVESTIGATING_SYNTAX`** (`IndentationError`, etc.)
1.  **Context:** Basic Python syntax error at `failing_line` of `failing_file`. Often caused by incomplete or malformed edits.
2.  **Action:** Use `read_file` to view `failing_line` and surrounding lines.
3.  **Analysis:** Identify the specific syntax issue (e.g., missing colon, incorrect indentation, unmatched parenthesis).
4.  **Action:** Formulate the minimal code edit to fix the syntax. Be careful not to remove necessary logic if the error resulted from a bad previous edit attempt. May require reading more context.
5.  **Action:** Store `fix_description="Correcting syntax error"` and `code_edit_details={...}`.
6.  **Transition:** `APPLYING_FIX`.
7.  **Error Handling:** If `read_file` fails unexpectedly, consider attempting a 'blind' fix based only on the line number and error type, or transition to `FAILED`.

---

**State: `INVESTIGATING_OTHER`**
1.  Follow similar investigate -> analyze -> formulate fix steps for other specific, known error types.
2.  **Transition:** `APPLYING_FIX` or `FAILED`.

---

**State: `APPLYING_FIX`**
1.  **Context:** Have `fix_description` and `code_edit_details` from internal state.
2.  **Action:** Execute `edit_file` using `code_edit_details`, providing `fix_description` as the `instructions`.
3.  **Decision:** Check `edit_file` result.
    *   If successful: **Transition:** `VERIFYING_FIX`.
    *   If failed (e.g., edit rejected, file not found despite previous checks): **Transition:** `FAILED`.

---

**State: `VERIFYING_FIX`**
1.  **Action:** Execute `run_terminal_cmd` with `command={{COMMAND_TO_RUN_APP}}`.
2.  **Transition:** `ANALYZING_OUTPUT`.

---

**State: `SUCCESS`**
1.  **Action:** Report success. Include a summary of fixes applied (number of attempts, descriptions of fixes).
2.  **End Workflow.**

---

**State: `FAILED`**
1.  **Action:** Report failure. Include the last error encountered, the number of attempts made, and a summary of fixes attempted.
2.  **End Workflow.**

--- 