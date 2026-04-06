import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_env_example_exists():
    """.env.example file exists at project root."""
    assert os.path.isfile(os.path.join(PROJECT_ROOT, ".env.example"))


def test_env_example_contains_all_vars():
    """.env.example documents all required configuration variables (INFRA-02)."""
    env_path = os.path.join(PROJECT_ROOT, ".env.example")
    with open(env_path) as f:
        content = f.read()

    required_vars = [
        "APP_PORT",
        "DB_PATH",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "NOTIFY_DAYS_BEFORE",
        "SQL_ECHO",
    ]
    for var in required_vars:
        assert var in content, f"{var} not found in .env.example"


def test_gitignore_has_env():
    """.env is listed in .gitignore (INFRA-02)."""
    gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
    with open(gitignore_path) as f:
        lines = [line.strip() for line in f.readlines()]
    assert ".env" in lines
