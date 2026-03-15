import streamlit as st
import subprocess
import tempfile
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse

PROFILE_DIR = Path.home() / ".claude" / "skills" / "apply" / "profile"
TEMPLATES_DIR = Path.home() / ".claude" / "skills" / "apply" / "templates"
CLAUDE_CMD = str(Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd")

st.set_page_config(
    page_title="Job Apply Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stExpander > div:first-child { border-radius: 8px; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"[File not found: {path}]"

def load_profiles():
    return {
        "resume":      read_file(PROFILE_DIR / "resume.md"),
        "stories":     read_file(PROFILE_DIR / "stories.md"),
        "preferences": read_file(PROFILE_DIR / "preferences.md"),
    }

def load_templates():
    return {
        "cold_email":   read_file(TEMPLATES_DIR / "cold-email.md"),
        "linkedin":     read_file(TEMPLATES_DIR / "linkedin-message.md"),
        "cover_letter": read_file(TEMPLATES_DIR / "cover-letter.md"),
        "referral":     read_file(TEMPLATES_DIR / "referral-request.md"),
        "slack":        read_file(TEMPLATES_DIR / "slack-message.md"),
    }

def is_url(text: str) -> bool:
    text = text.strip()
    try:
        result = urlparse(text)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False

def fetch_job_posting(url: str) -> tuple[str, str | None]:
    """Returns (job_text, error_message). error_message is None on success."""
    domain = urlparse(url).netloc.lower()

    if "linkedin.com" in domain:
        return "", "LinkedIn blocks automated scraping. Please copy and paste the job description text directly."

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return "", "Request timed out. Try pasting the job description directly."
    except requests.exceptions.HTTPError as e:
        return "", f"Could not fetch page ({e.response.status_code}). Try pasting the job description directly."
    except Exception as e:
        return "", f"Could not fetch URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Site-specific extractors
    job_text = ""

    if "greenhouse.io" in domain or "boards.greenhouse.io" in domain:
        container = soup.find(id="app_body") or soup.find(class_="app-body")
        if container:
            job_text = container.get_text(separator="\n", strip=True)

    elif "lever.co" in domain:
        container = soup.find(class_="posting") or soup.find(class_="content")
        if container:
            job_text = container.get_text(separator="\n", strip=True)

    elif "workday.com" in domain or "myworkdayjobs.com" in domain:
        container = soup.find(attrs={"data-automation-id": "jobPostingDescription"})
        if container:
            job_text = container.get_text(separator="\n", strip=True)

    elif "ashbyhq.com" in domain or "jobs.ashbyhq.com" in domain:
        container = soup.find(class_="ashby-job-posting-brief-description") or soup.find("main")
        if container:
            job_text = container.get_text(separator="\n", strip=True)

    elif "wellfound.com" in domain or "angel.co" in domain:
        container = soup.find(class_="job-description") or soup.find("main")
        if container:
            job_text = container.get_text(separator="\n", strip=True)

    # Generic fallback
    if not job_text:
        main = soup.find("main") or soup.find(id="main") or soup.find(class_="main")
        if main:
            job_text = main.get_text(separator="\n", strip=True)
        else:
            job_text = soup.get_text(separator="\n", strip=True)

    # Trim excessive whitespace lines
    lines = [l.strip() for l in job_text.splitlines()]
    job_text = "\n".join(l for l in lines if l)

    if len(job_text) < 100:
        return "", "Could not extract job content from the page. Try pasting the job description directly."

    return job_text[:12000], None  # cap at 12k chars


def build_prompt(profiles: dict, templates: dict, selected_types: list, job_text: str) -> str:
    return f"""You are a world-class career coach and copywriter. Generate hyper-personalized job application content.

=== CANDIDATE RESUME ===
{profiles['resume']}

=== CANDIDATE PROFESSIONAL STORIES (STAR FORMAT) ===
{profiles['stories']}

=== COMMUNICATION PREFERENCES & BRAND RULES ===
{profiles['preferences']}

=== TEMPLATES TO FOLLOW ===

--- COLD EMAIL TEMPLATE ---
{templates['cold_email']}

--- LINKEDIN MESSAGE TEMPLATE ---
{templates['linkedin']}

--- COVER LETTER TEMPLATE ---
{templates['cover_letter']}

--- REFERRAL REQUEST TEMPLATE ---
{templates['referral']}

--- SLACK MESSAGE TEMPLATE ---
{templates['slack']}

=== INSTRUCTIONS ===
Generate the following content types for this job posting: {', '.join(selected_types)}

1. Extract: company name, role title, key requirements, culture signals, pain points being solved.
2. Match the candidate's most relevant experience and stories to the role's requirements.
3. Generate ONLY the content types listed above.
4. Follow each template's structure and constraints exactly.
5. Every piece of content must be specific to THIS company and role -- never generic.
6. Include at least one concrete metric per piece of content.
7. Never use "I'm passionate about", "I came across your posting", or any generic opener.
8. Never use em dashes -- use a comma, period, or rewrite instead.
9. Format each content type clearly with a header line like:
   === COLD EMAIL (TO HIRING MANAGER) ===
   [content]
   === END ===
10. After all content, add 2-3 bullets explaining the strategic choices made for this specific application.

JOB POSTING:
{job_text}"""

def check_claude_cli() -> bool:
    return Path(CLAUDE_CMD).exists()

def run_claude(prompt: str) -> tuple[str, str | None]:
    """Returns (output, error). error is None on success."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(prompt)
        tmp_path = tmp.name

    # Convert Unix-style paths (from Git Bash) to proper Windows paths for cmd.exe.
    # e.g. /c/Users/... -> C:\Users\...
    def to_win_path(p: str) -> str:
        try:
            result = subprocess.run(["cygpath", "-w", p], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        # Fallback: manual conversion for /c/Users/... style paths
        if len(p) > 2 and p[0] == "/" and p[2] == "/":
            return p[1].upper() + ":\\" + p[3:].replace("/", "\\")
        return p.replace("/", "\\")

    win_path = to_win_path(tmp_path)
    claude_win = to_win_path(CLAUDE_CMD)

    # cmd.exe stdin redirection: prompt is piped from file, never passed as a
    # CLI argument -- avoids Windows' 8191-char command line limit.
    cmd_str = f'"{claude_win}" --output-format text -p - < "{win_path}"'

    try:
        process = subprocess.Popen(
            ["cmd", "/c", cmd_str],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = process.communicate()
        Path(tmp_path).unlink(missing_ok=True)

        if process.returncode != 0:
            err = stderr_bytes.decode("utf-8", errors="replace")
            return "", f"Claude CLI error: {err}"

        return stdout_bytes.decode("utf-8", errors="replace"), None
    except FileNotFoundError:
        return "", "Claude CLI not found. Make sure Claude Code is installed."
    except Exception as e:
        return "", str(e)

def parse_sections(text: str) -> list[tuple[str, str]]:
    sections = []
    current_section = None
    current_content = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("===") and "END" not in stripped:
            if current_section and current_content:
                sections.append((current_section, "\n".join(current_content).strip()))
            current_section = stripped.replace("===", "").strip()
            current_content = []
        elif stripped.startswith("===") and "END" in stripped:
            if current_section and current_content:
                sections.append((current_section, "\n".join(current_content).strip()))
            current_section = None
            current_content = []
        elif current_section is not None:
            current_content.append(line)
    return sections

# ── sidebar ──────────────────────────────────────────────────────────────────

CONTENT_TYPES = [
    "Cold Email (Hiring Manager)",
    "Cold Email (Recruiter)",
    "LinkedIn Connection Request",
    "LinkedIn Follow-up Message",
    "Cover Letter",
    "Referral Request",
    "Slack Message",
]

claude_available = check_claude_cli()

with st.sidebar:
    st.title("💼 Job Apply Agent")
    st.markdown("---")

    if claude_available:
        st.success("Claude CLI connected")
        st.caption("Using your Claude Pro account via OAuth -- no API key needed.")
    else:
        st.error("Claude CLI not found")
        st.caption("Install Claude Code CLI and run `claude login`.")

    st.markdown("---")
    st.markdown("**Profile Status**")
    for label, filename in [("Resume", "resume.md"), ("Stories", "stories.md"), ("Preferences", "preferences.md")]:
        path = PROFILE_DIR / filename
        if not path.exists():
            st.error(f"Missing: {label}")
        elif "[Your Full Name]" in path.read_text(encoding="utf-8"):
            st.warning(f"Needs filling in: {label}")
        else:
            st.success(f"Ready: {label}")

    st.markdown("---")
    if st.button("Open Profile Files", use_container_width=True):
        st.info(f"Profile files are at:\n`{PROFILE_DIR}`")

# ── main ─────────────────────────────────────────────────────────────────────

st.title("Generate Job Application Content")

col1, col2 = st.columns([2, 1])

with col1:
    job_input = st.text_input(
        "Job Posting URL",
        placeholder="https://boards.greenhouse.io/company/jobs/123 or paste a job description below",
        help="Paste a URL to auto-fetch the job posting, or type/paste the description below."
    )
    job_text_fallback = st.text_area(
        "Or paste job description directly",
        placeholder="Paste the full job description here if you don't have a URL...",
        height=220,
    )

with col2:
    st.markdown("**What to generate:**")
    selected = {label: st.checkbox(label, value=True) for label in CONTENT_TYPES}
    st.markdown("---")
    generate_btn = st.button("Generate", type="primary", use_container_width=True, disabled=not claude_available)
    if not claude_available:
        st.caption("Claude CLI not found. Install Claude Code and log in.")

# ── generation ────────────────────────────────────────────────────────────────

if generate_btn:
    selected_types = [label for label, checked in selected.items() if checked]
    if not selected_types:
        st.warning("Select at least one content type.")
        st.stop()

    raw_input = job_input.strip()
    job_text = ""

    if raw_input and is_url(raw_input):
        with st.spinner(f"Fetching job posting from {urlparse(raw_input).netloc}..."):
            job_text, err = fetch_job_posting(raw_input)
        if err:
            st.error(err)
            st.stop()
        st.success(f"Fetched {len(job_text)} characters from the job posting.")
    elif raw_input:
        job_text = raw_input
    elif job_text_fallback.strip():
        job_text = job_text_fallback.strip()
    else:
        st.warning("Enter a job posting URL or paste a description.")
        st.stop()

    profiles = load_profiles()
    templates = load_templates()
    prompt = build_prompt(profiles, templates, selected_types, job_text)

    st.markdown("---")
    st.markdown("### Generated Content")

    with st.spinner("Generating via Claude CLI... (this takes 20-40 seconds)"):
        full_response, err = run_claude(prompt)

    if err:
        st.error(err)
        st.stop()

    sections = parse_sections(full_response)

    if sections:
        for title, content in sections:
            with st.expander(title, expanded=True):
                st.text_area(
                    label="",
                    value=content,
                    height=max(150, min(400, content.count("\n") * 22 + 60)),
                    key=f"output_{title}",
                    help="Ctrl+A then Ctrl+C to copy"
                )
    else:
        st.text_area("Full Output", value=full_response, height=600)

    st.success("Done. Click inside any box and press Ctrl+A, Ctrl+C to copy.")
