# CLAUDE.md -- Job Apply Agent

## Rules to Always Follow

- Never use em dashes in any generated content -- use a comma, period, or rewrite instead.
- Never be generic -- every sentence must be specific to the company and role.
- Never use "I'm passionate about..." -- show passion through specificity.
- Always include at least one concrete metric per piece of content.

## Changelog Rule

**Every major change, bug fix, architectural decision, or new feature must be logged in CHANGELOG.md before committing.**

Each entry must include:
- What changed
- Why the previous approach failed or was insufficient (for bug fixes)
- What approach was chosen and why

This applies to all changes: code fixes, prompt updates, dependency changes, infrastructure decisions.

## Error and Fix Communication Rule

**Before suggesting or applying any fix, always explain:**
1. What the error is
2. The root cause of the error
3. The exact change being made
4. Why the fix works
5. What impact it will have on the app

Do not apply any fix without this explanation first. Wait for user approval before proceeding.
