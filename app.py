"""
app.py
----------------
Main Streamlit application entry point for the AI Lesson Plan Generator.

Run with:
    streamlit run app.py

AI generation is handled by ai_generator.py.
Database operations are handled by database.py.
Export operations are handled by excel_export.py, pdf_export.py
and doc_export.py.
"""

from __future__ import annotations

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
    new_lesson_id,
    safe_filename,
    truncate,
    validate_inputs,
)


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="AI Lesson Plan Generator",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_error_message(exc: Exception) -> str:
    """
    Safely get an error message from exceptions.
    Returns the string representation of the exception safely.
    """
    return str(exc) or "Unknown error"


def clear_editor_state():
    """
    Clear old editor widget values before loading a different lesson.
    """
    st.session_state.pop("edit_lesson_title", None)

    for key, _label in SECTION_SCHEMA:
        st.session_state.pop(f"edit_{key}", None)


# =============================================================================
# CUSTOM UI STYLING + ANIMATIONS
# =============================================================================

def load_css():
    """
    Load the project's existing CSS file if available.
    """
    css_path = Path(__file__).parent / "assets" / "style.css"

    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text()}</style>",
            unsafe_allow_html=True,
        )


load_css()


# -----------------------------------------------------------------------------
# Additional UI CSS
# -----------------------------------------------------------------------------

st.markdown(
    """
<style>

/* ============================================================
   ANIMATIONS
   ============================================================ */

@keyframes fadeIn {
    0% {
        opacity: 0;
        transform: translateY(14px);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes slideInLeft {
    0% {
        opacity: 0;
        transform: translateX(-18px);
    }
    100% {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes slideInRight {
    0% {
        opacity: 0;
        transform: translateX(18px);
    }
    100% {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes scaleIn {
    0% {
        opacity: 0;
        transform: scale(0.97);
    }
    100% {
        opacity: 1;
        transform: scale(1);
    }
}

@keyframes pulseGlow {
    0% {
        box-shadow: 0 0 0 rgba(59, 130, 246, 0);
    }
    50% {
        box-shadow: 0 0 16px rgba(59, 130, 246, 0.35);
    }
    100% {
        box-shadow: 0 0 0 rgba(59, 130, 246, 0);
    }
}

@keyframes successPop {
    0% {
        opacity: 0;
        transform: scale(0.95);
    }
    70% {
        transform: scale(1.01);
    }
    100% {
        opacity: 1;
        transform: scale(1);
    }
}


/* ============================================================
   MAIN CONTAINER & TEXT VISIBILITY
   ============================================================ */

.main .block-container {
    animation: fadeIn 0.5s ease-out;
    color: #1F2937 !important;
}

/* Base Body Text Enforcement */
.stApp p, .stApp span, .stApp div, .stApp li, .stApp label {
    color: #1F2937;
}


/* ============================================================
   HERO BANNER
   ============================================================ */

.hero-banner {
    animation: fadeIn 0.65s ease-out;
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    padding: 2.2rem 2rem;
    border-radius: 14px;
    margin-bottom: 2rem;
    box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
    transition: transform 0.3s ease;
}

.hero-banner:hover {
    transform: translateY(-2px);
}

.hero-banner h1 {
    color: #FFFFFF !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.5rem !important;
    animation: fadeIn 0.5s ease-out;
}

.hero-banner p {
    color: #DBEAFE !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
}


/* ============================================================
   HEADINGS
   ============================================================ */

h1, h2, h3, h4, h5, h6 {
    color: #1F2937 !important;
    animation: fadeIn 0.45s ease-out;
    font-weight: 700 !important;
}


/* ============================================================
   INPUT LABELS & DESCRIPTIONS
   ============================================================ */

[data-testid="stTextInput"] label, 
[data-testid="stTextInput"] label p,
[data-testid="stTextArea"] label,
[data-testid="stTextArea"] label p {
    color: #1F2937 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}


/* ============================================================
   INPUT BOXES & TEXTAREAS
   ============================================================ */

input, textarea {
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    background-color: #FFFFFF !important;
    caret-color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 8px !important;
    transition: all 0.25s ease !important;
}

input {
    font-size: 0.95rem !important;
}

textarea {
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
}

input::placeholder, textarea::placeholder {
    color: #6B7280 !important;
    -webkit-text-fill-color: #6B7280 !important;
}

input:focus, textarea:focus {
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    background-color: #FFFFFF !important;
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
}


/* ============================================================
   TEXT AREA CONTAINER
   ============================================================ */

[data-testid="stTextArea"] {
    animation: slideInLeft 0.35s ease-out;
}


/* ============================================================
   CARDS & CONTAINERS
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    animation: scaleIn 0.4s ease-out;
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.06);
}


/* ============================================================
   BUTTONS
   ============================================================ */

.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease, background-color 0.25s ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.stButton > button:active {
    transform: translateY(0);
}

/* Primary / Generate button */
button[kind="primary"] {
    animation: pulseGlow 2.5s infinite;
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: none !important;
}

button[kind="primary"]:hover {
    background-color: #1D4ED8 !important;
}


/* ============================================================
   DOWNLOAD BUTTONS
   ============================================================ */

.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
}

.stDownloadButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}


/* ============================================================
   EXPANDERS
   ============================================================ */

[data-testid="stExpander"] {
    animation: slideInLeft 0.35s ease-out;
    border-radius: 8px !important;
    border: 1px solid #E5E7EB !important;
    background-color: #FFFFFF !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

[data-testid="stExpander"]:hover {
    transform: translateX(2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

[data-testid="stExpander"] summary span {
    color: #1F2937 !important;
    font-weight: 600 !important;
}


/* ============================================================
   METADATA PILLS
   ============================================================ */

.meta-pill {
    display: inline-block;
    padding: 6px 14px;
    margin: 4px 6px 4px 0;
    border-radius: 20px;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    color: #1E40AF !important;
    font-weight: 600;
    font-size: 0.88rem;
    transition: all 0.25s ease;
}

.meta-pill:hover {
    transform: translateY(-2px);
    background: #DBEAFE;
}


/* ============================================================
   ALERTS
   ============================================================ */

[data-testid="stAlert"] {
    animation: successPop 0.4s ease-out;
    border-radius: 8px !important;
}

[data-testid="stAlert"] p {
    color: #1F2937 !important;
}


/* ============================================================
   PROGRESS
   ============================================================ */

[data-testid="stProgressBar"] {
    animation: fadeIn 0.4s ease-out;
}


/* ============================================================
   SIDEBAR
   ============================================================ */

[data-testid="stSidebar"] {
    animation: slideInLeft 0.45s ease-out;
    background-color: #1E293B !important;
}

[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] span, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #F8FAFC !important;
}

[data-testid="stSidebar"] hr {
    border-color: #334155 !important;
}


/* ============================================================
   CAPTIONS & HELPER TEXT
   ============================================================ */

.app-caption {
    color: #4B5563 !important;
    animation: fadeIn 0.5s ease-out;
}


/* ============================================================
   LESSON EDITOR INTRO
   ============================================================ */

.editor-intro {
    padding: 14px 18px;
    margin: 12px 0 20px 0;
    border-left: 4px solid #2563EB;
    background: #EFF6FF;
    border-radius: 8px;
    animation: slideInRight 0.45s ease-out;
    color: #1E3A8A !important;
}

.editor-intro strong {
    color: #1E40AF !important;
}

.editor-intro span {
    color: #1E3A8A !important;
}


/* ============================================================
   SAVE / EXPORT AREA
   ============================================================ */

.export-area {
    animation: fadeIn 0.5s ease-out;
}


/* ============================================================
   ABOUT PAGE CARDS
   ============================================================ */

.about-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    animation: fadeIn 0.5s ease-out;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.about-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
}

.about-card h3 {
    margin-top: 0 !important;
    color: #1F2937 !important;
}

.about-card p, .about-card li {
    color: #374151 !important;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-thumb {
    background: #CBD5E1;
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: #94A3B8;
}


/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 768px) {
    .meta-pill {
        display: block;
        width: fit-content;
    }

    textarea {
        font-size: 14px !important;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

try:
    init_db()

except DatabaseError as exc:
    st.error(
        f"⚠️ Database initialization failed: "
        f"{get_error_message(exc)}"
    )
    st.stop()


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():

    defaults = {
        "lesson": None,
        "lesson_id": None,
        "meta": {},
        "generated": False,
        "saved": False,
        "loaded_lesson_id": None,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.markdown("## 📘 Lesson Generator")

    st.markdown(
        "<span style='color:#94A3B8;'>"
        "AI-powered lesson planning for teachers"
        "</span>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    page = st.radio(
        "Navigate",
        options=[
            "✨ Generate Lesson",
            "🗂️ Lesson History",
            "ℹ️ About",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown(
        """
        <div style="
            padding: 14px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            animation: fadeIn 0.6s ease-out;
        ">
            <strong style="color: #60A5FA;">🤖 Powered by Gemini AI</strong>
            <br>
            <span style="font-size:0.84rem; color: #CBD5E1;">
                Generate classroom-ready lesson plans
                from a few simple inputs.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE: GENERATE LESSON
# =============================================================================

def render_generate_page():

    st.markdown(
        """
        <div class="hero-banner">
            <h1>✨ AI Lesson Plan Generator</h1>
            <p>
                Give us four details. We'll build a complete,
                classroom-ready lesson plan.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # INPUT CARD
    # -------------------------------------------------------------------------

    with st.container(border=True):

        st.subheader("📝 Lesson Details")

        col1, col2 = st.columns(2)

        with col1:

            subject = st.text_input(
                "Subject",
                placeholder="e.g. Science",
                key="input_subject",
            )

            topic = st.text_input(
                "Topic",
                placeholder="e.g. Photosynthesis",
                key="input_topic",
            )

        with col2:

            grade = st.text_input(
                "Class Grade",
                placeholder="e.g. 7",
                key="input_grade",
            )

            duration = st.text_input(
                "Duration of Lecture",
                placeholder="e.g. 45 Minutes",
                key="input_duration",
            )

        st.markdown(
            "<div style='height:4px;'></div>",
            unsafe_allow_html=True,
        )

        generate_clicked = st.button(
            "🚀 Generate Lesson Plan",
            type="primary",
            use_container_width=True,
        )

    # -------------------------------------------------------------------------
    # GENERATION
    # -------------------------------------------------------------------------

    if generate_clicked:

        errors = validate_inputs(
            subject,
            grade,
            topic,
            duration,
        )

        if errors:

            for err in errors:
                st.error(err)

        else:

            progress = st.progress(
                0,
                text="Preparing your lesson plan...",
            )

            try:

                progress.progress(
                    20,
                    text="🔍 Understanding your requirements...",
                )

                with st.spinner(
                    "🤖 Gemini is creating your lesson plan..."
                ):

                    progress.progress(
                        35,
                        text="🤖 Gemini is generating lesson content...",
                    )

                    lesson = generate_lesson_plan(
                        subject,
                        grade,
                        topic,
                        duration,
                    )

                    progress.progress(
                        85,
                        text="✨ Polishing your lesson plan...",
                    )

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

                progress.progress(
                    100,
                    text="🎉 Lesson plan ready!",
                )

                st.success(
                    "✅ Lesson plan generated successfully! "
                    "Scroll down to review and edit."
                )

            except LessonGenerationError as exc:

                progress.empty()

                st.error(
                    f"❌ Gemini could not generate the lesson plan.\n\n"
                    f"{get_error_message(exc)}"
                )

            except Exception as exc:

                progress.empty()

                st.error(
                    "❌ An unexpected error occurred while generating "
                    "the lesson plan.\n\n"
                    f"{get_error_message(exc)}"
                )

    # -------------------------------------------------------------------------
    # EDITOR
    # -------------------------------------------------------------------------

    if (
        st.session_state.generated
        and st.session_state.lesson
    ):

        render_lesson_editor()


# =============================================================================
# LESSON EDITOR
# =============================================================================

def render_lesson_editor():

    lesson = st.session_state.lesson
    meta = st.session_state.meta

    st.markdown("---")

    st.subheader(
        "🖊️ Review & Edit Your Lesson Plan"
    )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    st.markdown(
        f"""
        <div style="
            animation: fadeIn 0.5s ease-out;
            margin-bottom: 14px;
        ">
            <span class="meta-pill">
                📚 {meta.get('subject', '')}
            </span>
            <span class="meta-pill">
                🎓 Grade {meta.get('grade', '')}
            </span>
            <span class="meta-pill">
                🧩 {meta.get('topic', '')}
            </span>
            <span class="meta-pill">
                ⏱️ {meta.get('duration', '')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # EDITOR INTRO
    # -------------------------------------------------------------------------

    st.markdown(
        """
        <div class="editor-intro">
            <strong>✏️ Edit your lesson plan</strong>
            <br>
            <span>
                Open any section below and modify the generated content.
                Your changes will be used when you save or export the lesson.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # LESSON TITLE
    # -------------------------------------------------------------------------

    lesson["lesson_title"] = st.text_input(
        "Lesson Title",
        value=lesson.get("lesson_title", ""),
        key="edit_lesson_title",
    )

    # -------------------------------------------------------------------------
    # EDITABLE SECTIONS
    # -------------------------------------------------------------------------

    for index, (key, label) in enumerate(SECTION_SCHEMA):

        if key == "lesson_title":
            continue

        with st.expander(
            f"📌 {label}",
            expanded=False,
        ):

            widget_key = f"edit_{key}"

            height = (
                260
                if key in LONG_TEXT_SECTIONS
                else 160
            )

            new_value = st.text_area(
                label,
                value=lesson.get(key, ""),
                key=widget_key,
                height=height,
                label_visibility="collapsed",
            )

            lesson[key] = new_value

    st.session_state.lesson = lesson

    # =========================================================================
    # SAVE + EXPORT
    # =========================================================================

    st.markdown("---")

    st.markdown(
        """
        <div class="export-area">
            <h3>💾 Save & Export</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns(4)

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    with action_cols[0]:

        if st.button(
            "💾 Save Lesson",
            use_container_width=True,
        ):

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

                st.success(
                    "Lesson saved to history ✅"
                )

            except DatabaseError as exc:

                st.error(
                    f"❌ Could not save lesson: "
                    f"{get_error_message(exc)}"
                )

    base_filename = safe_filename(
        lesson.get("lesson_title")
        or meta.get("topic")
        or "Lesson"
    )

    # -------------------------------------------------------------------------
    # EXCEL
    # -------------------------------------------------------------------------

    with action_cols[1]:

        try:

            excel_bytes = build_excel_workbook(
                lesson,
                meta,
            )

            st.download_button(
                "📊 Download Excel",
                data=excel_bytes,
                file_name=f"{base_filename}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        except ExportError as exc:

            st.error(
                f"❌ Excel export failed: "
                f"{get_error_message(exc)}"
            )

    # -------------------------------------------------------------------------
    # PDF
    # -------------------------------------------------------------------------

    with action_cols[2]:

        try:

            pdf_bytes = build_pdf(
                lesson,
                meta,
            )

            st.download_button(
                "📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{base_filename}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        except ExportError as exc:

            st.error(
                f"❌ PDF export failed: "
                f"{get_error_message(exc)}"
            )

    # -------------------------------------------------------------------------
    # WORD
    # -------------------------------------------------------------------------

    with action_cols[3]:

        try:

            docx_bytes = build_docx(
                lesson,
                meta,
            )

            st.download_button(
                "📝 Download Word",
                data=docx_bytes,
                file_name=f"{base_filename}.docx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                use_container_width=True,
            )

        except ExportError as exc:

            st.error(
                f"❌ Word export failed: "
                f"{get_error_message(exc)}"
            )

    # -------------------------------------------------------------------------
    # SAVE STATUS
    # -------------------------------------------------------------------------

    if st.session_state.saved:

        st.caption(
            "✅ This lesson is saved in your Lesson History."
        )

    else:

        st.caption(
            "ℹ️ Click **Save Lesson** to keep this lesson "
            "in your history."
        )


# =============================================================================
# PAGE: LESSON HISTORY
# =============================================================================

def render_history_page():

    st.markdown(
        "## 🗂️ Lesson History"
    )

    st.markdown(
        """
        <p class='app-caption'>
            Browse, search, reload, or delete previously saved lesson plans.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------------------------

    with st.container(border=True):

        st.markdown("#### 🔎 Search Saved Lessons")

        col1, col2, col3 = st.columns(3)

        with col1:

            search_subject = st.text_input(
                "Subject contains",
                key="search_subject",
            )

        with col2:

            search_grade = st.text_input(
                "Grade contains",
                key="search_grade",
            )

        with col3:

            search_topic = st.text_input(
                "Topic contains",
                key="search_topic",
            )

    # -------------------------------------------------------------------------
    # FETCH LESSONS
    # -------------------------------------------------------------------------

    try:

        if (
            search_subject
            or search_grade
            or search_topic
        ):

            lessons = search_lessons(
                subject=search_subject or None,
                grade=search_grade or None,
                topic=search_topic or None,
            )

        else:

            lessons = get_all_lessons()

    except DatabaseError as exc:

        st.error(
            f"❌ Could not load lesson history: "
            f"{get_error_message(exc)}"
        )

        return

    # -------------------------------------------------------------------------
    # EMPTY STATE
    # -------------------------------------------------------------------------

    if not lessons:

        st.info(
            "📭 No saved lessons yet. "
            "Generate and save a lesson plan to see it here."
        )

        return

    st.markdown(
        f"**{len(lessons)} lesson(s) found**"
    )

    # -------------------------------------------------------------------------
    # LESSON LIST
    # -------------------------------------------------------------------------

    for record in lessons:

        title_preview = truncate(
            f"{record['subject']} • "
            f"Grade {record['grade']} • "
            f"{record['topic']}",
            90,
        )

        with st.container(border=True):

            cols = st.columns(
                [4, 2, 2, 2, 2]
            )

            with cols[0]:

                st.markdown(
                    f"**{title_preview}**"
                )

                st.caption(
                    f"Duration: {record['duration']} "
                    f"· Saved: {record['created_at']}"
                )

            with cols[1]:

                st.markdown(
                    f"📚 {record['subject']}"
                )

            with cols[2]:

                st.markdown(
                    f"🎓 Grade {record['grade']}"
                )

            with cols[3]:

                if st.button(
                    "🔄 Reload",
                    key=f"reload_{record['lesson_id']}",
                    use_container_width=True,
                ):

                    reload_lesson(
                        record["lesson_id"]
                    )

            with cols[4]:

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{record['lesson_id']}",
                    use_container_width=True,
                ):

                    try:

                        delete_lesson(
                            record["lesson_id"]
                        )

                        st.success(
                            "Lesson deleted."
                        )

                        st.rerun()

                    except DatabaseError as exc:

                        st.error(
                            f"❌ Could not delete lesson: "
                            f"{get_error_message(exc)}"
                        )


# =============================================================================
# RELOAD LESSON
# =============================================================================

def reload_lesson(lesson_id: str):

    try:

        record = get_lesson(lesson_id)

        if not record:
            st.error("❌ Lesson not found.")
            return

        clear_editor_state()

        st.session_state.lesson = record["lesson"]
        st.session_state.lesson_id = record["lesson_id"]
        st.session_state.meta = {
            "subject": record["subject"],
            "grade": record["grade"],
            "topic": record["topic"],
            "duration": record["duration"],
        }
        st.session_state.generated = True
        st.session_state.saved = True

        st.success("✅ Lesson reloaded! Redirecting to editor...")
        st.rerun()

    except DatabaseError as exc:
        st.error(
            f"❌ Could not reload lesson: "
            f"{get_error_message(exc)}"
        )


# =============================================================================
# PAGE: ABOUT
# =============================================================================

def render_about_page():

    st.markdown("## ℹ️ About AI Lesson Plan Generator")

    st.markdown(
        """
        <p class='app-caption'>
            An intelligent assistant designed to save teachers hours of preparation time.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="about-card">
            <h3>🚀 What is this application?</h3>
            <p>
                The <strong>AI Lesson Plan Generator</strong> creates detailed, structured, 
                and classroom-ready lesson plans in seconds using Google's Gemini AI. 
                Whether you need learning objectives, step-by-step activity timings, or assessment ideas, 
                this tool generates it instantly.
            </p>
        </div>

        <div class="about-card">
            <h3>✨ Key Features</h3>
            <ul>
                <li><strong>Gemini AI Integration:</strong> Structured pedagogical prompt engineering for realistic classroom plans.</li>
                <li><strong>Interactive Editor:</strong> Tweak, expand, or refine any part of the generated plan prior to exporting.</li>
                <li><strong>Multi-Format Exports:</strong> Download your finished lesson plans in Excel (.xlsx), Word (.docx), or PDF formats.</li>
                <li><strong>Local History Storage:</strong> Save your plans locally to search, edit, or reload whenever needed.</li>
            </ul>
        </div>

        <div class="about-card">
            <h3>🛠️ Tech Stack</h3>
            <p>
                Built with <strong>Streamlit</strong>, <strong>Google Gemini API</strong>, 
                <strong>SQLite</strong>, <strong>ReportLab</strong>, and <strong>python-docx</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# MAIN ROUTING
# =============================================================================

def main():

    if page == "✨ Generate Lesson":
        render_generate_page()

    elif page == "🗂️ Lesson History":
        render_history_page()

    elif page == "ℹ️ About":
        render_about_page()


if __name__ == "__main__":
    main()