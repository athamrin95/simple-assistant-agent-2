import os
import unittest
import tempfile
from dotenv import load_dotenv

class TestDotEnvLoading(unittest.TestCase):
    
    def test_load_dotenv_success(self):
        key = "API_KEY"
        value = "secret_key_123"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as temp_env:
            temp_env.write(f"{key}={value}")
            temp_env_path = temp_env.name

        try:
            if key in os.environ:
                del os.environ[key]

            success = load_dotenv(dotenv_path=temp_env_path)
            
            self.assertTrue(success, "load_dotenv() failed to load the .env file.")
            self.assertEqual(os.environ.get(key), value)

        finally:
            if os.path.exists(temp_env_path):
                os.unlink(temp_env_path)
            if key in os.environ:
                del os.environ[key]

if __name__ == "__main__":
    unittest.main()