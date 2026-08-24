"""
utils.py
----------------
Shared constants and helper utilities used across the AI Lesson Plan
Generator application. Keeping the section schema in one place means
every module (AI generator, exporters, database, UI) stays in sync.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Lesson section schema
# ---------------------------------------------------------------------------
# Each entry: (key, human-readable label)
# The "key" is what is used internally (dict key, DB column-ish, session
# state key). The "label" is what is displayed to the teacher in the UI
# and in exported documents.

SECTION_SCHEMA: List[tuple] = [
    ("lesson_title", "Lesson Title"),
    ("learning_objectives", "Learning Objectives"),
    ("learning_outcomes", "Expected Learning Outcomes"),
    ("blooms_taxonomy", "Bloom's Taxonomy Mapping"),
    ("prerequisite_knowledge", "Prerequisite Knowledge"),
    ("introduction", "Introduction"),
    ("hook_activity", "Hook Activity"),
    ("teacher_explanation", "Teacher Explanation"),
    ("teacher_script", "Teacher Script"),
    ("teaching_process", "Step-by-Step Teaching Process"),
    ("student_activities", "Student Activities"),
    ("hands_on_activity", "Hands-on Activity"),
    ("group_activity", "Group Activity"),
    ("real_life_examples", "Real-Life Examples"),
    ("classroom_discussion", "Classroom Discussion"),
    ("materials_needed", "Materials Needed"),
    ("time_allocation", "Time Allocation"),
    ("assessment_strategy", "Assessment Strategy"),
    ("mcqs", "MCQs"),
    ("short_answer_questions", "Short Answer Questions"),
    ("hots_questions", "Higher Order Thinking Questions"),
    ("exit_ticket", "Exit Ticket"),
    ("homework", "Homework"),
    ("reflection", "Reflection"),
    ("common_misconceptions", "Common Misconceptions"),
    ("teaching_tips", "Teaching Tips"),
    ("support_slow_learners", "Support for Slow Learners"),
    ("extension_activities", "Extension Activities for Advanced Students"),
    ("lesson_summary", "Lesson Summary"),
]

SECTION_KEYS = [k for k, _ in SECTION_SCHEMA]
SECTION_LABELS = {k: label for k, label in SECTION_SCHEMA}

# Sections that tend to be long-form free text -> rendered as text_area
LONG_TEXT_SECTIONS = {
    "teacher_script",
    "teaching_process",
    "student_activities",
    "introduction",
    "teacher_explanation",
    "classroom_discussion",
    "mcqs",
    "short_answer_questions",
    "hots_questions",
}


def new_lesson_id() -> str:
    """Generate a short, unique lesson identifier."""
    return uuid.uuid4().hex[:10]


def now_timestamp() -> str:
    """Return a human-readable timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def empty_lesson_dict() -> Dict[str, str]:
    """Return a lesson dict with every schema key set to an empty string."""
    return {key: "" for key in SECTION_KEYS}


def safe_filename(text: str) -> str:
    """Turn arbitrary text into a filesystem-safe filename fragment."""
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9_\-]", "", text)
    return text or "Lesson"


def markdown_to_plain_lines(markdown_text: str) -> List[str]:
    """
    Very small helper that strips the most common Markdown tokens
    (#, *, -, numbers) so exported PDFs/Word docs/Excel cells show
    clean plain text instead of raw Markdown syntax.
    """
    if not markdown_text:
        return []

    lines = markdown_text.split("\n")
    cleaned = []
    for line in lines:
        line = line.rstrip()
        line = re.sub(r"^#{1,6}\s*", "", line)          # headings
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)      # bold
        line = re.sub(r"\*(.*?)\*", r"\1", line)          # italics
        line = re.sub(r"^[-*]\s+", "• ", line)            # bullet lists
        cleaned.append(line)
    return cleaned


def markdown_to_plain_text(markdown_text: str) -> str:
    """Collapse cleaned Markdown lines back into a single plain string."""
    return "\n".join(markdown_to_plain_lines(markdown_text))


def truncate(text: str, length: int = 80) -> str:
    """Truncate text for compact display (e.g. history table previews)."""
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"


def validate_inputs(subject: str, grade: str, topic: str, duration: str) -> List[str]:
    """
    Validate the four teacher inputs. Returns a list of human-readable
    error messages; an empty list means validation passed.
    """
    errors = []
    if not subject or not subject.strip():
        errors.append("Please enter a Subject.")
    if not grade or not grade.strip():
        errors.append("Please enter a Grade.")
    if not topic or not topic.strip():
        errors.append("Please enter a Topic.")
    if not duration or not duration.strip():
        errors.append("Please enter a Duration.")
    return errors


def build_lesson_full_text(lesson: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """
    Combine metadata + all sections into one big plain-text blob.
    Used for quick previews and as a fallback "copy all" view.
    """
    parts = [
        f"Subject: {meta.get('subject', '')}",
        f"Grade: {meta.get('grade', '')}",
        f"Topic: {meta.get('topic', '')}",
        f"Duration: {meta.get('duration', '')}",
        "",
    ]
    for key, label in SECTION_SCHEMA:
        content = lesson.get(key, "")
        if content:
            parts.append(f"## {label}\n{content}\n")
    return "\n".join(parts)
