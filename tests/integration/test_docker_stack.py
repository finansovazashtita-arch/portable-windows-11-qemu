"""
Unit and Integration Tests for Production Docker Packaging & Compose Stack.
"""

import os
import unittest


class TestDockerStack(unittest.TestCase):
    """Test suite for Dockerfile and docker-compose.yml validation."""

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_dockerfile_exists_and_valid(self):
        dockerfile_path = os.path.join(self.root_dir, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM python:", content)
        self.assertIn("tesseract-ocr", content)
        self.assertIn("EXPOSE 8090", content)
        self.assertIn("scripts/microinvest_n8n_service.py", content)

    def test_docker_compose_exists_and_valid(self):
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path))

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("microinvest-ocr-service", content)
        self.assertIn("8090:8090", content)
        self.assertIn("INFISICAL_URL", content)
        self.assertIn("N8N_WEBHOOK_URL", content)

    def test_requirements_txt_exists(self):
        req_path = os.path.join(self.root_dir, "requirements.txt")
        self.assertTrue(os.path.exists(req_path))

        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("PyMuPDF", content)
        self.assertIn("pytesseract", content)


if __name__ == "__main__":
    unittest.main()
