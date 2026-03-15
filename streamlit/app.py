import streamlit as st
import subprocess
import os
import shutil
from pathlib import Path

PROFILE_DIR = Path.home() / ".claude" / "skills" / "apply" / "profile"
TEMPLATES_DIR = Path.home() / ".claude" / "skills" / "apply" / "templates"

st.set_page_config(
    page_title="Job Apply Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .output-box {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #cdd6f4;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .section-header {
        font-size: 16px;
        font-weight: 600;
        color: #89b4fa;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stExpander > div:first-child {
        border-radius: 8px;
    }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
</style>
""", unsafe_allow_html=True)

def read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"[File not found: {path}]"

def load_profiles():
    return {
        "resume": read_file(PROFILE_DIR / "resume.md"),
        "stories": read_file(PROFILE_DIR / "stories.md"),
        "preferences": read_file(PROFILE_DIR / "preferences.md"),
    }

def load_templates():
    return {
        "cold_email": read_file(TEMPLATES_DIR / "cold-email.md"),
        "linkedin": read_file(TEMPLATES_DIR / "linkedin-message.md"),
        "cover_letter": read_file(TEMPLATES_DIR / "cover-letter.md"),
        "referral": read_file(TEMPLATES_DIR / "referral-request.md"),
        "slack": read_file(TEMPLATES_DIR / "slack-message.md"),
    }

def build_prompt(profiles: dict, templates: dict, selected_types: list, job_input: str) -> str:
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
{job_input.strip()}"""

def check_claude_cli() -> bool:
    return shutil.which("claude") is not None

CONTENT_TYPES = {
    "Cold Email (Hiring Manager)": "cold_email_hm",
    "Cold Email (Recruiter)": "cold_email_recruiter",
    "LinkedIn Connection Request": "linkedin_connect",
    "LinkedIn Follow-up Message": "linkedin_followup",
    "Cover Letter": "cover_letter",
    "Referral Request": "referral",
    "Slack Message": "slack",
}

claude_available = check_claude_cli()

# Sidebar
with st.sidebar:
    st.title("💼 Job Apply Agent")
    st.markdown("---")

    if claude_available:
        st.success("Claude CLI connected")
        st.caption("Using your Claude Pro account via OAuth -- no API key needed.")
    else:
        st.error("Claude CLI not found")
        st.caption("Make sure Claude Code is installed and you are logged in.")

    st.markdown("---")
    st.markdown("**Profile Status**")

    for label, filename in [("Resume", "resume.md"), ("Stories", "stories.md"), ("Preferences", "preferences.md")]:
        path = PROFILE_DIR / filename
        has_placeholder = "[Your Full Name]" in path.read_text(encoding="utf-8") if path.exists() else False
        if not path.exists():
            st.error(f"Missing: {label}")
        elif has_placeholder:
            st.warning(f"Needs filling in: {label}")
        else:
            st.success(f"Ready: {label}")

    st.markdown("---")
    if st.button("Open Profile Files", use_container_width=True):
        st.info(f"Profile files are at:\n`{PROFILE_DIR}`")

# Main area
st.title("Generate Job Application Content")
st.markdown("Paste a job description below, select what to generate, and click **Generate**.")

col1, col2 = st.columns([2, 1])

with col1:
    job_input = st.text_area(
        "Job Posting",
        placeholder="Paste the full job description here...\n\nTip: include the company name, role title, and requirements for best results.",
        height=300,
        help="Paste the full job description. The more detail, the better the output."
    )

with col2:
    st.markdown("**What to generate:**")
    selected = {}
    for label in CONTENT_TYPES:
        selected[label] = st.checkbox(label, value=True)

    st.markdown("---")
    generate_btn = st.button(
        "Generate",
        type="primary",
        use_container_width=True,
        disabled=not claude_available
    )

    if not claude_available:
        st.caption("Claude CLI not found. Install Claude Code and log in.")

# Generation
if generate_btn and job_input.strip():
    selected_types = [label for label, checked in selected.items() if checked]

    if not selected_types:
        st.warning("Select at least one content type to generate.")
        st.stop()

    profiles = load_profiles()
    templates = load_templates()
    prompt = build_prompt(profiles, templates, selected_types, job_input)

    st.markdown("---")
    st.markdown("### Generated Content")
    st.caption("Generating via Claude CLI...")

    output_placeholder = st.empty()
    full_response = ""

    try:
        process = subprocess.Popen(
            ["claude", "-p", prompt, "--output-format", "text"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        for line in process.stdout:
            full_response += line
            output_placeholder.markdown(full_response + "...")

        process.wait()

        if process.returncode != 0:
            err = process.stderr.read()
            st.error(f"Claude CLI error: {err}")
            st.stop()

        output_placeholder.empty()

        # Parse sections
        sections = []
        current_section = None
        current_content = []

        for line in full_response.split('\n'):
            stripped = line.strip()
            if stripped.startswith('===') and 'END' not in stripped:
                if current_section and current_content:
                    sections.append((current_section, '\n'.join(current_content).strip()))
                current_section = stripped.replace('===', '').strip()
                current_content = []
            elif stripped.startswith('===') and 'END' in stripped:
                if current_section and current_content:
                    sections.append((current_section, '\n'.join(current_content).strip()))
                current_section = None
                current_content = []
            else:
                if current_section is not None:
                    current_content.append(line)

        if sections:
            for title, content in sections:
                with st.expander(f"  {title}", expanded=True):
                    st.text_area(
                        label="",
                        value=content,
                        height=max(150, min(400, content.count('\n') * 22 + 60)),
                        key=f"output_{title}",
                        help="Click in the box and Ctrl+A, Ctrl+C to copy all"
                    )
        else:
            st.text_area("Full Output", value=full_response, height=600, help="Select all and copy")

        st.success("Done. Click inside any text box and press Ctrl+A then Ctrl+C to copy.")

    except FileNotFoundError:
        st.error("Claude CLI not found. Make sure Claude Code is installed.")
    except Exception as e:
        st.error(f"Error: {e}")

elif generate_btn and not job_input.strip():
    st.warning("Paste a job description first.")
