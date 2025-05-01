# text-to-sql-transaltion


# 🧠 Arabic-to-SQL Translation Project

This project focuses on converting Arabic natural language questions into executable SQL queries using a large language model (LLM). It evaluates the accuracy of generated queries by comparing them to ground truth SQL queries over real SQLite databases.

## 🚀 Project Overview

- **Goal**: Translate Arabic questions into valid SQL queries using schema-aware prompting and evaluate performance.
- **Approach**:
  - Extract schema from `.sqlite` databases and corresponding `.sql` files.
  - Prompt a language model (e.g., LLaMA 3.1 via NVIDIA API) with Arabic questions + schema context.
  - Compare generated queries against true SQL queries using result matching.

---

## 🗃️ [Dataset](https://www.kaggle.com/datasets/mazenmahmoud79/txttosql-nlp)

- Format: JSONL file with fields:
  - `arabic`: The natural language question in Arabic.
  - `query`: The ground-truth SQL query.
  - `db_id`: Corresponding database ID (used to load the `.sqlite` and `.sql` files).
  - `question `: The natural language question in English.


Example entry:
```json
{
  "question":"How many heads of the departments are older than 56 ?"
  "query":"SELECT count(*) FROM head WHERE age > 56"
  "arabic":"كم عدد رؤساء الأقسام الذين تزيد أعمارهم عن 56 سنة؟"
  "db_id":"department_management"
}
```

The main dataset used is located in:
```
Text To SQL Task/Dataset/AR_spider.jsonl
```

---

## 🛠️ Key Features

- **Schema Extraction**: Uses SQLite PRAGMA statements to extract table and column metadata.
- **Clean SQL Outputs**: Removes formatting artifacts like markdown and comments from LLM outputs.
- **LLM Query Generation**: Prompts LLMs (e.g., LLaMA 3.1 via NVIDIA API) with task-specific instructions.
- **Evaluation Framework**: Automatically executes both true and predicted queries and compares the results.
- **Sample Logging**: Saves evaluated samples and results in a JSONL file for audit and inspection.

---

## 💡 Improvements

- Integrated manual review process to fix incorrect SQL generations:
  - Used **ChatGPT** as an assistant to refine broken or ambiguous SQL queries.
  - Collected **expert SQL feedback** to guide LLM prompt optimization and correctness checks.

---

## 🔧 How to Run

### 1. Install Dependencies
```bash
pip install openai sqlite3
```

### 2. Set API Configuration
Update your API key and endpoint in the `main()` function:
```python
lm_api_key = "<YOUR_API_KEY>"
lm_endpoint = "https://api.openai.com/v1/completions"  # or NVIDIA endpoint
```

### 3. Run the Main Script
```bash
python main.py
```

---

## 📁 Project Structure

```text
.
├── main.py                # Core logic for translation and evaluation
├── Text To SQL Task/
│   ├── Dataset/
│   │   ├── AR_spider.jsonl           # Arabic question dataset
│   │   └── database/
│       ├── academic/
│       │   ├── academic.sqlite       # SQLite database file
│       │   └── schema.sql            # Corresponding SQL schema file
└── evaluated_output.jsonl            # (Optional) Logged predictions
```

---

## 📊 Evaluation

- Compares **true vs predicted SQL outputs** by executing both on the same `.sqlite` database.
- Accuracy = `90% of predictions that match the exact query result`.

You can run partial evaluations using:
```python
evaluate_translation(jsonl_file, lm_api_key, lm_endpoint, schema_base_path, sample_size=10)
```

---

## 🧠 Notes & Challenges

- **Prompt tuning** was critical: schema clarity, instruction wording, and length limits impacted quality.
- Some SQL queries from the dataset required **manual corrections** due to ambiguous logic or outdated syntax.
- LLM responses were sanitized and validated for edge cases (e.g., empty outputs, SQL errors).

---

## 📍 Future Work

- Integrate **retriever-based schema summarization** for large databases.
- Add **interactive web interface** for live Arabic-to-SQL conversion.
- Explore **few-shot and in-context learning** for handling novel schemas.

