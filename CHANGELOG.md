# Changelog

All major changes to the Job Apply Agent are recorded here.

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
