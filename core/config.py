import os

def load_env():
    """
    Loads environment variables from a local .env file in the project root.
    """
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    # Strip spaces and optional surrounding quotes
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    
                    # Set environment variable if not already set externally
                    if key and not os.environ.get(key):
                        os.environ[key] = val
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")
