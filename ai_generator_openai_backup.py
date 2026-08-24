"""
ai_generator.py
----------------
Handles all communication with the OpenAI API using the official
OpenAI Python SDK and the Responses API.

Responsibilities:
    * Build the system + user prompt for lesson-plan generation.
    * Call the OpenAI Responses API and request a strict JSON object
      back (one field per lesson section) so the rest of the app can
      work with structured data instead of parsing free-form Markdown.
    * Surface clear, user-friendly exceptions for the UI layer to catch
      (missing key, invalid key, network problems, API errors, bad
      JSON, etc).

No Streamlit imports live in this file on purpose -- it should be
usable/testable completely independently of the UI layer.
"""

from __future__ import annotations

import json
import os
from typing import Dict

from openai import (
    OpenAI,
    AuthenticationError,
    APIConnectionError,
    APIStatusError,
    RateLimitError,
)

from utils import SECTION_SCHEMA, empty_lesson_dict

# The model used for generation. Kept as a constant so it's easy to swap.
MODEL_NAME = "gpt-4o-mini"


class LessonGenerationError(Exception):
    """Raised whenever lesson generation fails for any reason.

    The `.user_message` attribute is always safe to show directly in
    the Streamlit UI (no raw stack traces / internal details leaked).
    """

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def _get_client() -> OpenAI:
    """
    Build an OpenAI client using the OPENAI_API_KEY environment
    variable. Never hardcode the key -- always read it from the
    environment, and fail with a friendly error if it's missing.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise LessonGenerationError(
            "No OpenAI API key was found. Please set the OPENAI_API_KEY "
            "environment variable before running the app."
        )
    return OpenAI(api_key=api_key)


def _build_system_prompt() -> str:
    """
    The system prompt instructs the model to behave like a veteran
    (25+ years) classroom teacher, follow Bloom's Taxonomy, use
    age-appropriate language, avoid hallucination, and -- critically --
    return ONLY a JSON object matching our section schema so the UI can
    render editable fields directly.
    """
    schema_keys = ", ".join(f'"{key}"' for key, _ in SECTION_SCHEMA)

    return f"""You are an experienced educator and instructional designer with
over 25 years of classroom teaching experience across multiple subjects
and grade levels. You design classroom-ready, age-appropriate,
practical, and engaging lesson plans.

Follow these principles strictly:
- Map objectives and activities to Bloom's Taxonomy (Remember, Understand,
  Apply, Analyze, Evaluate, Create).
- Use age-appropriate language and examples for the given grade level.
- Design engaging, practical, hands-on classroom activities.
- Include realistic, usable assessments (MCQs, short answer, and higher
  order thinking questions).
- Never invent unsafe, inappropriate, or factually incorrect content.
  If uncertain about a specific fact, keep the statement general rather
  than fabricating specifics.
- Maintain a professional, classroom-ready tone throughout.
- Write in clear, well-structured Markdown inside each field (you may use
  bullet points, numbered steps, and short headings within a field's text).
- Be concrete and practical, not vague or generic filler.

You must respond with STRICT JSON ONLY -- no preamble, no explanation,
no Markdown code fences, and no text outside the JSON object. The JSON
object must contain exactly these string keys, each holding a
well-formatted Markdown string as its value: {schema_keys}.

Every value must be non-empty and genuinely useful to a classroom
teacher preparing to teach this specific lesson."""


def _build_user_prompt(subject: str, grade: str, topic: str, duration: str) -> str:
    return f"""Create a complete, classroom-ready lesson plan for the following:

Subject: {subject}
Grade: {grade}
Topic: {topic}
Duration: {duration}

Generate rich, specific, age-appropriate content for every required
section. Make it feel like it was written by a master teacher who knows
this grade level well, not generic filler text."""


def generate_lesson_plan(subject: str, grade: str, topic: str, duration: str) -> Dict[str, str]:
    """
    Call the OpenAI Responses API and return a dict matching
    SECTION_SCHEMA keys -> generated Markdown content.

    Raises LessonGenerationError with a friendly message on any failure
    (missing/invalid key, no internet, API error, malformed response).
    """
    client = _get_client()

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(subject, grade, topic, duration)

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={"format": {"type": "json_object"}},
            temperature=0.7,
        )
    except AuthenticationError:
        raise LessonGenerationError(
            "The OpenAI API key appears to be invalid. Please check your "
            "OPENAI_API_KEY environment variable and try again."
        )
    except APIConnectionError:
        raise LessonGenerationError(
            "Could not reach the OpenAI API. Please check your internet "
            "connection and try again."
        )
    except RateLimitError:
        raise LessonGenerationError(
            "The OpenAI API rate limit or quota has been reached. Please "
            "wait a moment and try again, or check your API plan."
        )
    except APIStatusError as exc:
        raise LessonGenerationError(
            f"The OpenAI API returned an error (status {exc.status_code}). "
            "Please try again in a moment."
        )
    except Exception:
        raise LessonGenerationError(
            "An unexpected error occurred while contacting the OpenAI API. "
            "Please try again."
        )

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        raise LessonGenerationError(
            "The AI returned an empty response. Please try generating the "
            "lesson plan again."
        )

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        raise LessonGenerationError(
            "The AI response could not be parsed. Please try generating "
            "the lesson plan again."
        )

    # Normalize into our known schema so downstream code never has to
    # guard against missing keys.
    lesson = empty_lesson_dict()
    for key, _ in SECTION_SCHEMA:
        value = data.get(key, "")
        if isinstance(value, (list, dict)):
            # Defensive: if the model nests structured data, flatten it
            # into readable Markdown text instead of crashing the UI.
            value = json.dumps(value, indent=2, ensure_ascii=False)
        lesson[key] = str(value).strip()

    return lesson
