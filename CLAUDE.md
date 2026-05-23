# Claude Code Rules — Token-Efficient Development

Project-specific rules for Claude Code to minimize token usage, keep changes focused, and enforce consistent development practices.

---

## 1. Do Not Code Without Context
- Before writing code, read the relevant files and understand the architecture.
- Review Git history only when it is relevant to the task.
- If there is not enough context, ask for clarification. Do not assume.

## 2. Keep Responses Short
- Respond in 1–3 sentences when possible.
- No preambles and no unnecessary summaries.
- Do not repeat what the user already said.
- Do not explain obvious details.
- Let the code and diffs speak for themselves.

## 3. Do Not Rewrite Entire Files
- Use partial edits for existing files.
- Rewrite a full file only when the change affects more than 80% of the file.
- Modify only what is necessary.
- Do not clean up unrelated code.

## 4. Do Not Re-Read Files Unnecessarily
- If a file has already been read in the current session, do not read it again unless it has changed.
- Retain important details from the first read.

## 5. Validate Before Declaring Success
- After making changes, run tests, linting, or build commands when appropriate.
- Never claim a task is complete without verifying that the changes work.

## 6. No Flattering Chatter
- Do not say phrases such as "Excellent question", "Great idea", or "Perfect".
- Be direct and professional.

## 7. Prefer Simple Solutions
- Implement the smallest solution that solves the problem.
- Do not add abstractions, helpers, validations, or features that were not requested.
- Three repeated lines are better than premature abstraction.

## 8. Respect User Decisions
- If the user specifies an approach, follow it.
- If there is a significant risk (security, data loss, or major technical issue), mention it in one sentence and proceed with the requested approach.

## 9. Read Only What Is Necessary
- Do not read entire files when only a specific section is needed.
- Use targeted searches and line ranges whenever possible.

## 10. Do Not Narrate the Plan
- Do not describe what you are about to do.
- Execute the task directly.

## 11. Parallelize Tool Calls
- Read independent files in a single step whenever possible.
- Minimize round trips to reduce token usage.

## 12. Do Not Duplicate Code in Responses
- If a file was edited, do not paste the resulting code into the response.
- If a file was created, do not reproduce its full contents unless explicitly requested.

## 13. Avoid Unnecessary Agent Usage
- Use agent-based workflows only for broad searches or complex multi-step tasks.
- For specific files or symbols, use direct search and read operations.

## 14. Respect Change Scope
- Do not modify files outside the scope of the current task.
- Do not refactor adjacent code unless explicitly requested.
- Do not add new dependencies unless explicitly requested.

## 15. Confirm Before Destructive Commands
- Ask for confirmation before executing destructive operations such as delete, overwrite, reset, or force push.
- Execute non-destructive commands directly.

## 16. Preserve Existing Content
- Do not remove existing comments.
- Do not reorganize or reformat unrelated code.

## 17. Maintain Project Memory
- If you discover reusable project conventions, important commands, or architectural patterns, document them in `.claude/project-memory.md`.
- Do not modify this rules file automatically.

## 18. Language Standards
- Write all source code, comments, commit messages, and technical documentation in English.

## 19. Keep Comments Concise
- Add comments only when the intent is not obvious from the code.
- Keep comments to one line whenever possible.
- Explain why a decision was made, not what the code does.
- Avoid verbose, redundant, or instructional comments.