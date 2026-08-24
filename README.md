# 📘 AI Lesson Plan Generator

An AI-powered, teacher-focused Streamlit application that turns four
simple inputs — **Subject, Grade, Topic, Duration** — into a complete,
classroom-ready lesson plan: objectives, activities, assessments,
differentiation strategies, and more. Review and edit every section,
then export to **Excel**, **PDF**, or **Word** with one click.

---

## ✨ Features

- **Just 4 inputs** — Subject, Grade, Topic, Duration. The AI figures out everything else.
- **Comprehensive lesson content** — learning objectives, Bloom's Taxonomy mapping,
  hook activities, teacher script, step-by-step teaching process, hands-on and
  group activities, assessments (MCQs, short answer, higher-order thinking),
  exit tickets, homework, differentiation for slow learners and advanced students,
  and more.
- **Full in-app editing** — every generated section is editable before you save or export.
- **One-click export** — professionally formatted Excel (.xlsx), PDF, and Word (.docx) files.
- **Lesson History** — save, search, reload, and delete past lesson plans (SQLite).
- **Polished, modern UI** — sidebar navigation, cards, expanders, progress indicators,
  and a clean color palette designed to feel like a commercial ed-tech product.
- **Robust error handling** — friendly messages for missing/invalid API keys, network
  issues, empty inputs, database errors, and export failures.

---

## 🗂️ Folder Structure

```
AI_Lesson_Generator/
│
├── app.py              # Main Streamlit application (UI + routing)
├── ai_generator.py      # OpenAI Responses API integration & prompt engineering
├── database.py          # SQLite persistence (save / search / delete / reload)
├── excel_export.py       # Excel (.xlsx) export via OpenPyXL
├── pdf_export.py         # PDF export via ReportLab
├── doc_export.py         # Word (.docx) export via python-docx
├── utils.py              # Shared section schema & helper functions
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── assets/
    └── style.css         # Custom UI styling
```

---

## 🛠️ Installation

### 1. Clone / download the project

Place the `AI_Lesson_Generator` folder wherever you'd like to run it from.

### 2. Create a virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your OpenAI API key

Never hardcode your API key — the app reads it from the `OPENAI_API_KEY`
environment variable.

**macOS / Linux:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

You can also create a `.env` file and load it with a tool of your choice,
as long as `OPENAI_API_KEY` ends up in the process environment before
Streamlit starts.

### 5. Run the app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 📸 Screenshots

_Add screenshots of the Generate Lesson page, the editable lesson view,
and the Lesson History page here once you've run the app locally._

---

## 🚀 Future Improvements

- Multi-language lesson plan generation.
- Curriculum-standard alignment (e.g. CBSE, Common Core, IB).
- Collaborative lesson plans shared across a school/department.
- Rich-text (WYSIWYG) editing instead of plain text areas.
- User accounts and per-teacher lesson libraries.
- Batch generation of a full unit/term's worth of lessons.

---

## 🧰 Tech Stack

Python · Streamlit · OpenAI Python SDK (Responses API) · SQLite ·
OpenPyXL · python-docx · ReportLab · Pandas · Markdown
