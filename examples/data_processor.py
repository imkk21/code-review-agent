import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    # Bug 1: Mutable default argument shared across instances
    def __init__(self, processing_history=[]):
        self.history = processing_history

    # Bug 2: Division by zero risk
    def calculate_average_score(self, scores):
        total = sum(scores)
        # Missing check if scores is empty before division
        avg = total / len(scores) 
        return avg

    # Bug 3: Logging sensitive PII and secrets
    def process_billing_record(self, user_id, credit_card, cvc, amount):
        # Leakage of credit card and CVC secrets in log files
        logger.info(f"Processing card payment for user {user_id}: card={credit_card}, cvc={cvc}, amount={amount}")
        self.history.append({"user": user_id, "amount": amount})
        return True

    # Bug 4: Dangerous deserialization of untrusted user input using pickle
    def load_user_session(self, session_bytes):
        # Unsafe unpickling allows arbitrary code execution if session_bytes is user-controlled
        data = pickle.loads(session_bytes)
        logger.info("Session loaded successfully")
        return data

    # Bug 5: Logic bug with default parameter shadowing or incorrect range bounds
    def extract_sublist(self, items, start=0, end=None):
        if end is None:
            end = len(items) - 1 # Logic error: should be len(items) to get full list inclusive
        sub = []
        for i in range(start, end):  # range is exclusive of end, meaning last element is skipped
            sub.append(items[i])
        return sub
