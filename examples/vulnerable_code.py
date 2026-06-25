import os
import sqlite3

# SEC-001: Hardcoded Secret
API_KEY = "KGAT_ea34dc35c5f3e3fef822bcbb14944036"

# STYLE-001: Mutable Default Argument
def fetch_user_data(user_id: str, results=[]) -> list:
    # SEC-002: SQL Injection Risk
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
    
    # STYLE-002: Print Statement Debugging
    print(f"Debug: Query executed: {query}")
    
    row = cursor.fetchone()
    if row:
        results.append(row)
    conn.close()
    return results

def process_items(items: list) -> str:
    # PERF-001: Inefficient String Concatenation in loop
    result_str = ""
    for item in items:
        result_str += str(item)
    return result_str

def execute_user_command(user_cmd: str):
    # SEC-003: Dangerous Eval
    return eval(user_cmd)
