# Changelog

All major changes to the Job Apply Agent are recorded here.

---

## [v1.5.0] - 2026-03-15

### Fixed
- `streamlit/app.py`: "Filename, directory name, or volume label syntax is incorrect" from cmd.exe.
- **Root cause:** Python's `tempfile` returns Unix-style paths (`/c/Users/...`) in the Git Bash environment. The previous `.replace("/", "\\")` produced `\c\Users\...` instead of `C:\Users\...`, which cmd.exe rejected as an invalid path.
- **Fix:** Added `to_win_path()` helper that calls `cygpath -w` (Git Bash utility) to correctly convert Unix paths to Windows paths. Manual fallback handles the `/x/...` -> `X:\...` pattern if `cygpath` is unavailable.

### Added
- `CLAUDE.md`: Added "Error and Fix Communication Rule" -- every error must be explained (root cause, fix, why it works, impact) and approved before applying.

---

## [v1.4.0] - 2026-03-15

### Fixed
- `streamlit/app.py`: Resolved persistent "command line too long" error on Windows.
- **Why previous attempts failed:**
  - v1.2 used `-p "prompt"` directly -- hit Windows' 8191-char CLI limit.
  - v1.3 used PowerShell `$p = Get-Content file; claude -p $p` -- looked safe but PowerShell still passes `$p` as a CLI argument when forking the child process, hitting the same limit.
- **Fix chosen:** `cmd /c "claude.cmd -p - < prompt.txt"` -- cmd.exe stdin redirection pipes the file into claude's stdin before the process starts. The prompt never appears on any command line.

### Added
- `CLAUDE.md`: Project rules file. Enforces that every major change must be logged in CHANGELOG before committing.

---

## [v1.3.0] - 2026-03-15

### Added
- `streamlit/app.py`: URL input field -- paste a job posting URL to auto-fetch and parse the job content.
- Site-specific extractors for Greenhouse, Lever, Workday, Ashby, Wellfound. Generic BeautifulSoup fallback for all other job boards.
- Clear error message when LinkedIn URL is detected (LinkedIn blocks scraping).
- Paste-text fallback field retained for when no URL is available.
- `streamlit/requirements.txt`: Added `requests>=2.31` and `beautifulsoup4>=4.12`.

### Fixed
- `streamlit/app.py`: Switched from Anthropic SDK to PowerShell + temp file to route around Windows CLI length limit. (Later superseded by v1.4.0 fix.)

---

## [v1.2.0] - 2026-03-15

### Changed
- `streamlit/app.py`: Removed Anthropic SDK and API key requirement entirely.
- App now calls the `claude` CLI via subprocess, using the user's existing Claude Pro OAuth session.
- Sidebar shows Claude CLI connection status instead of API key input.
- `streamlit/requirements.txt`: Removed `anthropic` dependency -- only `streamlit` required.

### Fixed
- `streamlit/app.py`: `st.success(..., icon="✓")` crashed because Streamlit only accepts emoji characters in the `icon` parameter. Removed the `icon` argument.

---

## [v1.1.0] - 2026-03-14

### Changed
- `SKILL.md`: Replaced em dashes with double hyphens in existing rules
- `SKILL.md`: Added rule to never use em dashes in any generated content

---

## [v1.0.0] - 2026-03-14

Initial release. Full project built from scratch.

### Added

**Claude Code Skill (`/apply`)**
- `SKILL.md`: Core skill entry point. Takes a job posting URL or pasted description and generates tailored outreach content using the user's profile files and templates.
- `profile/resume.md`: Template for the user's work history, skills, and accomplishments.
- `profile/stories.md`: Template for STAR-format professional stories matched to job requirements.
- `profile/preferences.md`: Template for tone, brand rules, length constraints, and content do's/don'ts.
- `templates/cold-email.md`: Structure and constraints for cold emails to hiring managers and recruiters.
- `templates/linkedin-message.md`: Templates for LinkedIn connection requests and follow-up messages.
- `templates/cover-letter.md`: Three-paragraph cover letter structure with anti-patterns.
- `templates/referral-request.md`: Warm and loose-connection referral request templates.
- `templates/slack-message.md`: Community Slack and direct DM outreach templates.
- `examples/example-outputs.md`: Placeholder file for saving successful generated outputs over time.

**Streamlit Web UI (`streamlit/`)**
- `streamlit/app.py`: Local web app (~200 lines of Python). Reads profile files directly from disk. Features: job description text area, per-content-type checkboxes, real-time streaming output, collapsible result cards with copy-friendly text areas, API key input, model selector, profile status indicators in sidebar.
- `streamlit/requirements.txt`: `streamlit>=1.30`, `anthropic>=0.40`.

**Chrome Extension (`extension/`)**
- `extension/manifest.json`: Manifest V3. Targets LinkedIn, Greenhouse, Lever, Workday, Ashby, Jobvite, SmartRecruiters, Wellfound. Side panel + `Alt+A` hotkey.
- `extension/content-script.js`: Auto-extracts job title, company, and description from job board pages. Site-specific extractors for LinkedIn, Greenhouse, Lever, Workday, Ashby. Generic heuristic fallback for any other site. Caps extracted text at 8,000 characters.
- `extension/background.js`: Service worker. Receives extracted job data, loads profile/template files from `chrome.storage.local`, calls Anthropic API with streaming, forwards chunks to side panel.
- `extension/sidepanel.html` + `sidepanel.css` + `sidepanel.js`: Full side panel UI. States: idle, job-detected banner, generating (with live stream preview), results (collapsible cards per content type with copy buttons), error, setup prompt.
- `extension/options.html` + `options.js`: Settings page for API key, model selection, and profile file upload (resume, stories, preferences imported into `chrome.storage.local`).
- `extension/icons/`: Purple briefcase icon at 16x16, 48x48, and 128x128.

**Repo scaffolding**
- `.gitignore`: Excludes `profile/` files (personal data), `examples/example-outputs.md`, Python cache, `.env`, and editor files.
- `CHANGELOG.md`: This file.
