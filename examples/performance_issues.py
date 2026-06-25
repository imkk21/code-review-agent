import time
import asyncio
import sqlite3

class PerformanceTracker:
    def __init__(self, db_path="metrics.db"):
        self.db_path = db_path

    # Bottleneck 1: N+1 Query Problem
    def get_users_with_logs(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            
            results = []
            for user in users:
                user_id = user[0]
                # Executing a database query per user inside a loop (N+1 query problem)
                cursor.execute(f"SELECT action, timestamp FROM logs WHERE user_id = {user_id}")
                logs = cursor.fetchall()
                results.append({
                    "user": user[1],
                    "logs": [{"action": l[0], "time": l[1]} for l in logs]
                })
            return results

    # Bottleneck 2: Async blocking I/O using time.sleep
    async def fetch_api_data_async(self, urls):
        results = []
        for url in urls:
            # Blocking the entire asyncio event loop with synchronous sleep
            time.sleep(1.0) 
            results.append(f"Data from {url}")
        return results

    # Bottleneck 3: Quadratic lookup complexity O(N^2)
    def find_common_items(self, list_a, list_b):
        common = []
        # Inefficient O(N^2) intersection check instead of using a set (O(N))
        for item_a in list_a:
            if item_a in list_b:  # Linear search inside list_b repeated N times
                if item_a not in common:
                    common.append(item_a)
        return common

    # Bottleneck 4: Inefficient string accumulation inside loop
    def build_report(self, records):
        report = ""
        for record in records:
            # Re-allocating string memory on every iteration
            report += f"Record ID: {record['id']}\nName: {record['name']}\n---\n"
        return report
