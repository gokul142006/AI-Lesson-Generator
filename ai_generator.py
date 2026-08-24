import os
import json
from google import genai
from google.genai import types


class LessonGenerationError(Exception):
    """Raised when lesson generation fails."""
    pass


def generate_lesson_plan(subject, grade, topic, duration):
    """
    Generate a structured lesson plan using Gemini.
    Returns a Python dictionary.
    """

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise LessonGenerationError(
            "GEMINI_API_KEY is not set."
        )

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
Create a complete, classroom-ready lesson plan.

Subject: {subject}
Grade: {grade}
Topic: {topic}
Duration: {duration} minutes

The lesson must be practical and easy for a teacher to conduct.

Create the lesson plan with these sections:

1. Lesson Title
2. Learning Objectives
3. Required Materials
4. Introduction / Warm-up
5. Teaching / Explanation
6. Classroom Activities
7. Student Practice
8. Assessment
9. Homework
10. Teacher Notes

Make the content appropriate for Grade {grade}.

Return ONLY valid JSON matching the requested structure.
Do not use Markdown.
Do not add explanations outside the JSON.
"""

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "lesson_title": {
                    "type": "STRING"
                },
                "learning_objectives": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "required_materials": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "introduction": {
                    "type": "STRING"
                },
                "teaching_explanation": {
                    "type": "STRING"
                },
                "classroom_activities": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "student_practice": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "assessment": {
                    "type": "STRING"
                },
                "homework": {
                    "type": "STRING"
                },
                "teacher_notes": {
                    "type": "STRING"
                }
            },
            "required": [
                "lesson_title",
                "learning_objectives",
                "required_materials",
                "introduction",
                "teaching_explanation",
                "classroom_activities",
                "student_practice",
                "assessment",
                "homework",
                "teacher_notes"
            ]
        }

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )
        )

        if not response.text:
            raise LessonGenerationError(
                "Gemini returned an empty response."
            )

        try:
            lesson = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise LessonGenerationError(
                f"Gemini returned invalid JSON: {e}"
            )

        if not isinstance(lesson, dict):
            raise LessonGenerationError(
                "Gemini response is not a JSON object."
            )

        return lesson

    except LessonGenerationError:
        raise

    except Exception as e:
        raise LessonGenerationError(
            f"Gemini API error: {str(e)}"
        )
