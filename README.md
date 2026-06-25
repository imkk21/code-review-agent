# Autonomous AI Code Review Agent - Core Engine Prototype

This repository contains a local, fully functional prototype of the **Core Review Engine** (Phases 1 & 2 of the MVP blueprint). It includes static analysis rule matching (Multi-Signal Fusion) combined with Gemini LLM reviews returning structured JSON results.

## 🚀 Key Features

* **Multi-Signal Fusion**: Runs deterministic, local regex-based lint/security rules (e.g., SQL injection, hardcoded secrets, mutable defaults) and passes results as hints to the LLM.
* **Diff-Aware Reviews**: Parses git diffs to identify exactly which line numbers were modified, ensuring comments are only left on modified code hunks.
* **Structured Response Schema**: Leverages Gemini's structured output capability to return a validated Pydantic object detailing issue severity, explanation, and drop-in code fixes.
* **Dual Operation Mode**: Automatically runs in **LLM mode** if a `GEMINI_API_KEY` is configured, or falls back gracefully to a **Rule-Based Mock mode** to demonstrate functionality key-free.

---

## 🛠️ Installation & Setup

1. **Virtual Environment & Dependencies**:
   A virtual environment has already been created in this folder.
   To run commands, use the local python executable inside the `venv` directory:
   ```bash
   # Windows PowerShell
   .\venv\Scripts\python.exe main.py --help
   ```

2. **Configure API Key (Optional but Recommended)**:
   To run full LLM reviews, set your Gemini API key:
   ```powershell
   $env:GEMINI_API_KEY="your-gemini-api-key-here"
   ```

---

## 💻 How to Run

### 1. Command-Line Interface (`main.py`)

* **Review a single file** (simulates reviewing all lines of code):
  ```bash
  .\venv\Scripts\python.exe main.py --file examples/vulnerable_code.py
  ```

* **Review clean code** (demonstrates false-positive filtration):
  ```bash
  .\venv\Scripts\python.exe main.py --file examples/clean_code.py
  ```

* **Review unstaged git changes** in the repository:
  ```bash
  .\venv\Scripts\python.exe main.py --git
  ```

* **Save report to a file**:
  ```bash
  .\venv\Scripts\python.exe main.py --file examples/vulnerable_code.py --output report.md
  ```

### 2. FastAPI Webhook Server (`app.py`)

Run the local server simulating a pull request webhook receiver:
```bash
.\venv\Scripts\python.exe -m uvicorn app:app --reload
```
The server will start at `http://127.0.0.1:8000`. You can visit the interactive docs at `http://127.0.0.1:8000/docs` to test the `/review-file` and `/webhook` endpoints.

---

## 🗂️ Project Structure

```
├── requirements.txt         # Project dependencies
├── README.md                # This guide
├── core/
│   ├── __init__.py          # Marks core as a package
│   ├── models.py            # Pydantic schemas for response structure
│   ├── diff_parser.py       # Unified diff parser
│   ├── static_analysis.py   # Heuristic/regex security and style check rules
│   └── reviewer.py          # LLM review orchestrator & mock fallback
├── examples/
│   ├── vulnerable_code.py   # Example containing security/performance/style issues
│   └── clean_code.py        # Good example solving all issues securely
├── main.py                  # CLI entry point
└── app.py                   # FastAPI local server
```
