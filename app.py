"""
Streamlit front-end. This is a thin wrapper around agent.py -- every
button and chat message ultimately calls the same handle()/bootstrap()
functions the terminal app uses, so there's exactly one place the actual
agent logic lives.

Run with: streamlit run app.py
"""
import os
import streamlit as st
import pandas as pd

from models import AgentState
import agent
from config import RESUME_DIR, PDF_RESUME_DIR, REPORTS_DIR
import calendar_store
from redflags import check_all

st.set_page_config(page_title="Recruitment Agent", page_icon="🧑‍💼", layout="wide")


# ---------------------------------------------------------------------
# Session bootstrap - runs once per browser session
# ---------------------------------------------------------------------

if "state" not in st.session_state:
    st.session_state.state = AgentState()
    st.session_state.chat = []
    try:
        with st.spinner("Loading resumes and parsing the default JD... (first run downloads a small embedding model, needs internet)"):
            boot_msg = agent.bootstrap(st.session_state.state)
        st.session_state.chat.append(("assistant", boot_msg))
    except Exception as e:
        st.error(
            "Startup failed while loading resumes or the JD. This is almost always "
            "either a missing/invalid GEMINI_API_KEY in your .env file, or no internet "
            "access for the one-time embedding model download.\n\n"
            f"Details: {e}"
        )
        st.stop()

state: AgentState = st.session_state.state


def run_query(query: str):
    st.session_state.chat.append(("user", query))
    with st.spinner("Working on it..."):
        try:
            response = agent.handle(state, query)
        except Exception as e:
            response = f"Something went wrong handling that: {e}"
    st.session_state.chat.append(("assistant", response))


# ---------------------------------------------------------------------
# Sidebar - JD / resume management + quick actions
# ---------------------------------------------------------------------

with st.sidebar:
    st.title("HR Recruiter Dashboard")
    st.info(
        "Upload Job Descriptions, manage resumes, "
        "screen candidates, generate reports, and "
        "perform recruitment actions."
    )
    st.divider()
    st.header("📄 Job Description")
    if state.jd:
        st.caption(f"Currently loaded: **{state.jd.role}**")
        st.caption(f"{len(state.jd.required_skills)} required skills, {state.jd.min_experience_years}+ yrs")

    jd_file = st.file_uploader("Upload a JD (.txt)", type=["txt"], key="jd_upload")
    jd_pasted = st.text_area("...or paste a JD here", height=100, key="jd_paste")
    if st.button("Load JD"):
        raw = jd_file.read().decode("utf-8") if jd_file else jd_pasted
        with st.spinner("Parsing JD..."):
            msg = agent.apply_new_jd(state, raw)
        st.session_state.chat.append(("assistant", msg))
        st.rerun()

    st.divider()
    st.header("Resumes")
    st.caption(f"{len(state.candidates)} on file")

    uploaded = st.file_uploader(
        "Add resumes (.txt or .pdf)", type=["txt", "pdf"], accept_multiple_files=True, key="resume_upload"
    )
    if uploaded and st.button("Add & Reload"):
        os.makedirs(RESUME_DIR, exist_ok=True)
        os.makedirs(PDF_RESUME_DIR, exist_ok=True)
        for f in uploaded:
            target_dir = PDF_RESUME_DIR if f.name.lower().endswith(".pdf") else RESUME_DIR
            with open(os.path.join(target_dir, f.name), "wb") as out:
                out.write(f.read())
        with st.spinner("Re-indexing resumes..."):
            msg = agent.reload_candidates(state)
        st.session_state.chat.append(("assistant", msg))
        st.rerun()

    st.divider()
    st.header("Quick actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Top candidates", use_container_width=True):
            run_query("get me the top candidates")
            st.rerun()
        if st.button("Red flags", use_container_width=True):
            run_query("any red flags across the applicant pool")
            st.rerun()
    with col2:
        if st.button("Batch report", use_container_width=True):
            run_query("run a batch report")
            st.rerun()
        if st.button("Calendar", use_container_width=True):
            run_query("show the calendar")
            st.rerun()


# ---------------------------------------------------------------------
# Main area - chat + supporting tables
# ---------------------------------------------------------------------

st.title(" RecruitAI – Intelligent Recruitment Management Platform")

st.caption(
    "AI-powered recruitment platform that automates job description analysis, "
    "semantic resume screening, candidate ranking, interview preparation, "
    "salary intelligence, and end-to-end hiring workflows through a multi-agent architecture."
)

st.info(
    "👈 Open the **HR Recruiter Dashboard** from the left sidebar to upload Job Descriptions, "
    "manage resumes, access quick actions, and generate reports."
)

left, right = st.columns([2, 1])

with left:
    for role, text in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(text)

    # if the last handler call left a pending confirmation, surface it as
    # real buttons instead of making the recruiter type "yes"/"no"
    if state.pending_action:
        c1, c2 = st.columns(2)
        if c1.button(f"✅ Confirm: {state.pending_action.description}", key="confirm_yes"):
            run_query("yes")
            st.rerun()
        if c2.button("❌ Cancel", key="confirm_no"):
            run_query("no")
            st.rerun()

    query = st.chat_input("Ask about the JD, candidates, interviews, salary...")
    if query:
        run_query(query)
        st.rerun()

with right:
    st.subheader("Top ranked candidates")
    if state.last_ranked:
        df = pd.DataFrame([
            {
                "Name": sc.candidate.name,
                "Score": sc.match_score,
                "Exp (yrs)": sc.candidate.experience_years,
                "Matched skills": ", ".join(sc.matched_skills) or "-",
                "Missing skills": ", ".join(sc.missing_skills) or "-",
            }
            for sc in state.last_ranked
        ])
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.caption("Ask for the top candidates to see them ranked here.")

    st.subheader("Shortlist")
    if state.shortlist:
        for c in state.shortlist:
            st.markdown(f"- {c.name}")
    else:
        st.caption("Nothing shortlisted yet.")

    st.subheader("Scheduled interviews")
    slots = calendar_store.list_slots()
    if slots:
        for s in sorted(slots, key=lambda s: (s.date, s.time)):
            st.markdown(f"- {s.date} {s.time} -- {s.candidate_name}")
    else:
        st.caption("No interviews booked yet.")

    st.subheader("Red flags")
    flagged = check_all(state.candidates)
    if flagged:
        for r in flagged:
            with st.expander(r.candidate_name):
                for f in r.flags:
                    st.markdown(f"- {f}")
    else:
        st.caption("None detected in the current pool.")

    if os.path.isdir(REPORTS_DIR):
        reports = sorted(os.listdir(REPORTS_DIR), reverse=True)
        if reports:
            st.subheader("Batch reports")
            latest = os.path.join(REPORTS_DIR, reports[0])
            with open(latest, "r", encoding="utf-8") as f:
                st.download_button("Download latest report", f.read(), file_name=reports[0])
