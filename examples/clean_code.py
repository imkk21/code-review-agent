import os
import sqlite3
import logging

# Set up logging instead of print statements
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fixed SEC-001: API Key fetched from environment variables
API_KEY = os.environ.get("API_KEY")

# Fixed STYLE-001: None used as default, initialized inside
def fetch_user_data(user_id: str, results: list = None) -> list:
    if results is None:
        results = []
        
    # Fixed SEC-002: Parameterized query to avoid SQL Injection
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    
    # Fixed STYLE-002: Use logging instead of print
    logger.info("Query executed securely.")
    
    row = cursor.fetchone()
    if row:
        results.append(row)
    conn.close()
    return results

def process_items(items: list) -> str:
    # Fixed PERF-001: Efficient join instead of += in a loop
    return "".join(str(item) for item in items)

def execute_user_command(user_cmd: str):
    # Fixed SEC-003: Eliminated eval(), raise error or parse safely
    raise NotImplementedError("Arbitrary command execution is disabled for security reasons.")
