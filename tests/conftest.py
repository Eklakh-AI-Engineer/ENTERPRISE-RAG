import os
import sys
import pytest

# Ensure the project root is on the Python path so that "import app" works in tests.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

@pytest.fixture(autouse=True)
def mock_env_vars():
    os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_MODEL", "test-model")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
    os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-pub-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
