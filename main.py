import sqlite3
import json
import os
from openai import OpenAI
import random


def clean_sql(sql_text: str) -> str:
    """
    Cleans raw SQL text from model output.
g
    - Removes markdown code fences (e.g., ```sql)
    - Strips comments, extra whitespace

    Parameters:
        sql_text (str): Raw SQL text from model

    Returns:
        str: Cleaned SQL
    """
    lines = sql_text.strip().splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("```") or line.lower().startswith("--"):
            continue
        cleaned_lines.append(line)
    return " ".join(cleaned_lines)


def extract_schema(sqlite_file: str, schema_sql_file: str):
    """
    Extracts the table schema from the SQLite database and reads the SQL schema file.

    Parameters:
      sqlite_file (str): Path to the SQLite database file.
      schema_sql_file (str): Path to the schema SQL file.

    Returns:
      tuple: (extracted_schema_dict, schema_sql_str)
    """
    # Connect to the SQLite database and extract schema info
    schema = {}
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        # Each row is: (cid, name, type, notnull, dflt_value, pk)
        columns = cursor.fetchall()
        schema[table_name] = columns
    conn.close()

    # Read the schema SQL file
    with open(schema_sql_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    return schema, schema_sql


def execute_query(sql_query: str, db_path: str):
    """
    Executes a SQL query against a given SQLite database and returns the results as a list of tuples.
    Returns None on SQL errors.
    """
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Query Execution Error on {db_path}:\n{sql_query}\nError: {e}")
        return None


def translate_arabic_to_sql(arabic_sentence: str, schema_info: str, lm_api_key: str, lm_endpoint: str) -> str:
    """
    Translates an Arabic sentence into a SQL query by using a language model API.

    Parameters:
      arabic_sentence (str): The Arabic question to translate.
      schema_info (str): String with schema information to provide context.
      lm_api_key (str): API key for the language model.
      lm_endpoint (str): API endpoint URL for the language model.

    Returns:
      str: Generated SQL query (or None if an error occurs).
    """
    messages = [
        {
            "role": "system",
            "content": "You are a SQL expert who writes clean and correct SQL queries"
                       " based on Arabic natural language questions."
                       " Use only the relevant tables and columns from the database schema."
        },
        {
            "role": "user",
            "content": (
                f"Database Schema:\n{schema_info}\n\n"
                f"Arabic Question:\n{arabic_sentence}\n\n"
                f"Return the SQL query only, without any explanation or comments."
            )
        }
    ]
    print(messages)

    # Used to fix wrong sql queries in the orginal dataset
    # client = OpenAI(api_key="")
    # completion = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=messegs
    # )

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=lm_api_key
    )

    completion = client.chat.completions.create(
        model="nvidia/llama-3.1-nemotron-70b-instruct",
        messages=messages,
        temperature=0.1,
        top_p=1,
        max_tokens=1024,
        stream=True
    )
    response = ""
    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content
    response = clean_sql(response)
    print(f"Query response {response}")

    if response:
        generated_query = response
        return generated_query
    else:
        print(f"Error in LM API call: {response.status_code} {response.text}")
        return None



def save_single_sample(output_file: str, arabic_question: str, true_sql: str, db_id: str, predicted_sql: str):
    """
    Append a single evaluated sample into a JSONL file with predicted SQL.

    Args:
        output_file (str): Path to the output JSONL file.
        arabic_question (str): Arabic natural language question.
        true_sql (str): True SQL query (will be replaced by predicted SQL in output).
        db_id (str): Database ID.
        predicted_sql (str): Predicted SQL query to save.
    """
    output_data = {
        "arabic": arabic_question.strip(),
        "query": predicted_sql.strip(),  # Save the predicted SQL
        "db_id": db_id.strip()
    }

    with open(output_file, 'a', encoding='utf-8') as f:  # 'a' mode for appending
        f.write(json.dumps(output_data, ensure_ascii=False) + '\n')


def evaluate_translation(jsonl_file: str, lm_api_key: str, lm_endpoint: str, schema_base_path: str = ".",
                         sample_size: int = None, seed: int = 42) -> float:
    total = 0
    correct = 0

    # Set random seed for reproducibility
    random.seed(seed)

    # Step 1: Load all valid samples
    valid_samples = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            arabic_question = data.get("arabic", "").strip()
            true_sql = data.get("query", "").strip()
            db_id = data.get("db_id", "").strip()

            if arabic_question and true_sql and db_id:
                valid_samples.append(data)

    predicted_sqls = []
    # Step 2: Randomly sample if sample_size is set
    if sample_size is not None and sample_size < len(valid_samples):
        samples = random.sample(valid_samples, sample_size)
    else:
        samples = valid_samples

    # Step 3: Evaluate
    for data in samples:
        arabic_question = data["arabic"].strip()
        true_sql = data["query"].strip()
        db_id = data["db_id"].strip()

        print(arabic_question)
        print(true_sql)
        print(db_id)
        db_file_folder = os.path.join(schema_base_path, db_id)
        db_file_path = os.path.join(db_file_folder, f"{db_id}.sqlite")
        schema_sql_file = os.path.join(db_file_folder, "schema.sql")

        if not os.path.exists(db_file_path):
            print(f"Missing database for {db_id}")
            continue

        try:
            # Get schema for the current db
            schema_dict, schema_sql = extract_schema(db_file_path, schema_sql_file)
            schema_info = f"{schema_sql}\n\nExtracted Schema: {schema_dict}"
        except Exception as e:
            print(f"Error occurred while processing question: {db_file_path, schema_sql_file}")
            print(f"Error details: {e}")
            continue

        try:
            predicted_sql = translate_arabic_to_sql(arabic_question, schema_info, lm_api_key, lm_endpoint)
        # Get predicted SQL from LM
        # predicted_sql = translate_arabic_to_sql(arabic_question, schema_info, lm_api_key, lm_endpoint)
        except Exception as e:
            print(f"Error occurred while processing question: {arabic_question}")
            print(f"Error details: {e}")
            continue
            # Execute both queries

        pred_result = execute_query(predicted_sql, db_file_path)
        true_result = execute_query(true_sql, db_file_path)

        print(f"[DB: {db_id}] Arabic: {arabic_question}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"True SQL     : {true_sql}")
        print(f"Predicted Result: {pred_result}")
        print(f"True Result     : {true_result}")
        print("-" * 70)

        predicted_sqls.append(predicted_sql)
        if pred_result == true_result and pred_result is not None:
            correct += 1
        total += 1
        accuracy = (correct / total) * 100 if total > 0 else 0

        # save_single_sample("evaluated_output.jsonl", arabic_question, true_sql, db_id, predicted_sql)

        print(f"Final Accuracy: {accuracy:.2f}% ({correct}/{total})")
        if total == sample_size:
            break

    accuracy = (correct / total) * 100 if total > 0 else 0
    print(f"Final Accuracy: {accuracy:.2f}% ({correct}/{total})")
    return accuracy


def main():

    sqlite_file = "Text To SQL Task/Dataset/database/academic/academic.sqlite"
    schema_sql_file = "Text To SQL Task/Dataset/database/academic/schema.sql"
    jsonl_file = "Text To SQL Task/Dataset/AR_spider.jsonl"

    # Extract schema details from the SQLite database and the SQL file.
    schema_dict, schema_sql = extract_schema(sqlite_file, schema_sql_file)
    # Combine the schema information into a string that can be provided as context.
    schema_info = f"{schema_sql}\n\nExtracted Schema Details: {schema_dict}"
    # print(schema_info)

    # Set your LM API credentials and endpoint.
    # Example uses OpenAI's API; update lm_api_key and lm_endpoint for your LM of choice.
    lm_api_key = ""  # Replace with your LM API key
    lm_endpoint = "https://api.openai.com/v1/completions"  # Example endpoint; adjust as needed

    # Evaluate the Arabic-to-SQL translation on a sample of the dataset.
    # sample_size can be set to None to evaluate the entire file or to a specific number (e.g., 10).
    # evaluate_translation(jsonl_file, lm_api_key, lm_endpoint, schema_info, sample_size=10)

    schema_base_path = "Text To SQL Task/Dataset/database"  # directory with all .sqlite files and schema.sql
    evaluate_translation(jsonl_file, lm_api_key, lm_endpoint, schema_base_path, sample_size=10, seed=8)


if __name__ == "__main__":
    main()
