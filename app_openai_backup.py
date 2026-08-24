"""
app.py
----------------
Main Streamlit application entry point for the AI Lesson Plan Generator.

Run with:
    streamlit run app.py

This file is intentionally UI-only: all AI calls live in
ai_generator.py, all persistence lives in database.py, and all export
logic lives in {excel,pdf,doc}_export.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from ai_generator import LessonGenerationError, generate_lesson_plan
from database import (
    DatabaseError,
    delete_lesson,
    get_all_lessons,
    get_lesson,
    init_db,
    save_lesson,
    search_lessons,
)
from doc_export import build_docx
from excel_export import ExportError, build_excel_workbook
from pdf_export import build_pdf
from utils import (
    LONG_TEXT_SECTIONS,
    SECTION_SCHEMA,
    empty_lesson_dict,
    new_lesson_id,
    safe_filename,
    truncate,
    validate_inputs,
)

# -----------------------------------------------------------------------------
# Page configuration -- must be the first Streamlit call.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Lesson Plan Generator",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
def load_css():
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


load_css()


# -----------------------------------------------------------------------------
# Database init (safe to call every run -- CREATE TABLE IF NOT EXISTS)
# -----------------------------------------------------------------------------
try:
    init_db()
except DatabaseError as exc:
    st.error(f"⚠️ Database initialization failed: {exc.user_message}")
    st.stop()


# -----------------------------------------------------------------------------
# Session state defaults
# -----------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "lesson": None,           # dict of generated/edited lesson sections
        "lesson_id": None,        # current lesson's unique ID
        "meta": {},               # subject / grade / topic / duration
        "generated": False,       # whether a lesson has been generated this session
        "saved": False,           # whether current lesson has been saved
        "loaded_lesson_id": None, # if a lesson was reloaded from history
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📘 Lesson Generator")
    st.markdown(
        "<span style='color:#CBD5E1;'>AI-powered lesson planning for teachers</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    page = st.radio(
        "Navigate",
        options=["✨ Generate Lesson", "🗂️ Lesson History", "ℹ️ About"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    if api_key_present:
        st.success("API key detected ✅")
    else:
        st.warning("OPENAI_API_KEY not set ⚠️")

    st.markdown(
        "<span style='color:#94A3B8; font-size:0.8rem;'>"
        "Set the OPENAI_API_KEY environment variable before generating a lesson."
        "</span>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE: Generate Lesson
# =============================================================================
def render_generate_page():
    st.markdown(
        """
        <div class="hero-banner">
            <h1>✨ AI Lesson Plan Generator</h1>
            <p>Give us four details. We'll build a complete, classroom-ready lesson plan.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Input card ----------------------------------------------------------
    with st.container(border=True):
        st.subheader("📝 Lesson Details")
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject", placeholder="e.g. Science", key="input_subject")
            topic = st.text_input("Topic", placeholder="e.g. Photosynthesis", key="input_topic")
        with col2:
            grade = st.text_input("Grade", placeholder="e.g. 7", key="input_grade")
            duration = st.text_input("Duration", placeholder="e.g. 45 Minutes", key="input_duration")

        generate_clicked = st.button(
            "🚀 Generate Lesson Plan", type="primary", use_container_width=True
        )

    if generate_clicked:
        errors = validate_inputs(subject, grade, topic, duration)
        if errors:
            for err in errors:
                st.error(err)
        else:
            progress = st.progress(0, text="Preparing request...")
            try:
                with st.spinner("🧠 Generating lesson plan... this can take a few seconds"):
                    progress.progress(30, text="Contacting OpenAI...")
                    lesson = generate_lesson_plan(subject, grade, topic, duration)
                    progress.progress(90, text="Finalizing lesson plan...")

                st.session_state.lesson = lesson
                st.session_state.meta = {
                    "subject": subject.strip(),
                    "grade": grade.strip(),
                    "topic": topic.strip(),
                    "duration": duration.strip(),
                }
                st.session_state.lesson_id = new_lesson_id()
                st.session_state.generated = True
                st.session_state.saved = False
                progress.progress(100, text="Done!")
                st.success("✅ Lesson plan generated successfully! Scroll down to review and edit.")
            except LessonGenerationError as exc:
                progress.empty()
                st.error(f"❌ {exc.user_message}")
            except Exception as exc:  # last-resort safety net
                progress.empty()
                st.error(f"❌ An unexpected error occurred: {exc}")

    # --- Editable lesson section ------------------------------------------------
    if st.session_state.generated and st.session_state.lesson:
        render_lesson_editor()


def render_lesson_editor():
    lesson = st.session_state.lesson
    meta = st.session_state.meta

    st.markdown("---")
    st.subheader("🖊️ Review & Edit Your Lesson Plan")
    st.markdown(
        f"""
        <span class="meta-pill">📚 {meta.get('subject','')}</span>
        <span class="meta-pill">🎓 Grade {meta.get('grade','')}</span>
        <span class="meta-pill">🧩 {meta.get('topic','')}</span>
        <span class="meta-pill">⏱️ {meta.get('duration','')}</span>
        """,
        unsafe_allow_html=True,
    )

    lesson["lesson_title"] = st.text_input(
        "Lesson Title", value=lesson.get("lesson_title", ""), key="edit_lesson_title"
    )

    st.markdown(
        "<p class='app-caption'>Expand each section below to review and edit the "
        "AI-generated content. Your changes are saved automatically to this session "
        "and used for saving/exporting.</p>",
        unsafe_allow_html=True,
    )

    for key, label in SECTION_SCHEMA:
        if key == "lesson_title":
            continue
        with st.expander(f"📌 {label}", expanded=False):
            widget_key = f"edit_{key}"
            height = 220 if key in LONG_TEXT_SECTIONS else 140
            new_value = st.text_area(
                label,
                value=lesson.get(key, ""),
                key=widget_key,
                height=height,
                label_visibility="collapsed",
            )
            lesson[key] = new_value

    st.session_state.lesson = lesson

    # --- Save + Export actions -----------------------------------------------
    st.markdown("---")
    st.subheader("💾 Save & Export")

    action_cols = st.columns(4)

    with action_cols[0]:
        if st.button("💾 Save Lesson", use_container_width=True):
            try:
                save_lesson(
                    lesson_id=st.session_state.lesson_id,
                    subject=meta.get("subject", ""),
                    grade=meta.get("grade", ""),
                    topic=meta.get("topic", ""),
                    duration=meta.get("duration", ""),
                    lesson=lesson,
                )
                st.session_state.saved = True
                st.success("Lesson saved to history ✅")
            except DatabaseError as exc:
                st.error(f"❌ {exc.user_message}")

    base_filename = safe_filename(lesson.get("lesson_title") or meta.get("topic") or "Lesson")

    with action_cols[1]:
        try:
            excel_bytes = build_excel_workbook(lesson, meta)
            st.download_button(
                "📊 Download Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{base_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except ExportError as exc:
            st.error(f"❌ {exc.user_message}")

    with action_cols[2]:
        try:
            pdf_bytes = build_pdf(lesson, meta)
            st.download_button(
                "📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{base_filename}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except ExportError as exc:
            st.error(f"❌ {exc.user_message}")

    with action_cols[3]:
        try:
            docx_bytes = build_docx(lesson, meta)
            st.download_button(
                "📝 Download Word (.docx)",
                data=docx_bytes,
                file_name=f"{base_filename}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except ExportError as exc:
            st.error(f"❌ {exc.user_message}")

    if st.session_state.saved:
        st.caption("✅ This lesson is saved in your Lesson History.")
    else:
        st.caption("ℹ️ Remember to click **Save Lesson** to keep it in your history.")


# =============================================================================
# PAGE: Lesson History
# =============================================================================
def render_history_page():
    st.markdown("## 🗂️ Lesson History")
    st.markdown(
        "<p class='app-caption'>Browse, search, reload, or delete previously saved lesson plans.</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("#### 🔎 Search")
        col1, col2, col3 = st.columns(3)
        with col1:
            search_subject = st.text_input("Subject contains", key="search_subject")
        with col2:
            search_grade = st.text_input("Grade contains", key="search_grade")
        with col3:
            search_topic = st.text_input("Topic contains", key="search_topic")

    try:
        if search_subject or search_grade or search_topic:
            lessons = search_lessons(
                subject=search_subject or None,
                grade=search_grade or None,
                topic=search_topic or None,
            )
        else:
            lessons = get_all_lessons()
    except DatabaseError as exc:
        st.error(f"❌ {exc.user_message}")
        return

    if not lessons:
        st.info("No saved lessons yet. Generate and save a lesson plan to see it here.")
        return

    st.markdown(f"**{len(lessons)} lesson(s) found**")

    for record in lessons:
        title_preview = truncate(
            f"{record['subject']} • Grade {record['grade']} • {record['topic']}", 90
        )
        with st.container(border=True):
            cols = st.columns([4, 2, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{title_preview}**")
                st.caption(f"Duration: {record['duration']} · Saved: {record['created_at']}")
            with cols[1]:
                st.markdown(f"📚 {record['subject']}")
            with cols[2]:
                st.markdown(f"🎓 Grade {record['grade']}")
            with cols[3]:
                if st.button("🔄 Reload", key=f"reload_{record['lesson_id']}", use_container_width=True):
                    reload_lesson(record["lesson_id"])
            with cols[4]:
                if st.button("🗑️ Delete", key=f"delete_{record['lesson_id']}", use_container_width=True):
                    try:
                        delete_lesson(record["lesson_id"])
                        st.success("Lesson deleted.")
                        st.rerun()
                    except DatabaseError as exc:
                        st.error(f"❌ {exc.user_message}")


def reload_lesson(lesson_id: str):
    try:
        record = get_lesson(lesson_id)
    except DatabaseError as exc:
        st.error(f"❌ {exc.user_message}")
        return

    if record is None:
        st.error("That lesson could not be found. It may have been deleted.")
        return

    st.session_state.lesson = record["lesson"]
    st.session_state.meta = {
        "subject": record["subject"],
        "grade": record["grade"],
        "topic": record["topic"],
        "duration": record["duration"],
    }
    st.session_state.lesson_id = record["lesson_id"]
    st.session_state.generated = True
    st.session_state.saved = True
    st.session_state.loaded_lesson_id = lesson_id
    st.success("Lesson loaded! Switch to 'Generate Lesson' to review and export it.")


# =============================================================================
# PAGE: About
# =============================================================================
def render_about_page():
    st.markdown("## ℹ️ About This Application")
    with st.container(border=True):
        st.markdown(
            """
**AI Lesson Plan Generator** is a Streamlit-based application that helps
teachers create complete, classroom-ready lesson plans in seconds.

**How it works:**
1. Enter a Subject, Grade, Topic, and Duration.
2. The AI generates a full lesson plan covering objectives, activities,
   assessments, differentiation, and more — following Bloom's Taxonomy
   and age-appropriate best practices.
3. Review and edit every section directly in the app.
4. Save your lesson to history, and export it as Excel, PDF, or Word.

**Built with:** Streamlit, the OpenAI Python SDK (Responses API), SQLite,
OpenPyXL, python-docx, and ReportLab.
            """
        )


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
if page == "✨ Generate Lesson":
    render_generate_page()
elif page == "🗂️ Lesson History":
    render_history_page()
else:
    render_about_page()
