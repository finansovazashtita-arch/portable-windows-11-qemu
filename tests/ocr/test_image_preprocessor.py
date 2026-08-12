"""
Unit tests for Autonomous OCR Image Quality Enhancement Engine.
"""

import os
import tempfile
import unittest
from PIL import Image

from src.ocr.image_preprocessor import ImagePreprocessor


class TestImagePreprocessor(unittest.TestCase):
    """Test suite for ImagePreprocessor."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_image = os.path.join(self.temp_dir.name, "test_scan.png")
        self.output_image = os.path.join(self.temp_dir.name, "test_scan_enhanced.png")

        # Create sample synthetic test image
        img = Image.new("RGB", (200, 100), color=(200, 200, 200))
        img.save(self.input_image)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preprocess_image_execution(self):
        out_path = ImagePreprocessor.preprocess_image(self.input_image, self.output_image)
        self.assertTrue(os.path.exists(out_path))
        self.assertEqual(out_path, self.output_image)

        with Image.open(out_path) as img:
            self.assertEqual(img.size, (200, 100))

    def test_enhance_contrast_and_sharpness(self):
        with Image.open(self.input_image) as img:
            enhanced = ImagePreprocessor.enhance_contrast_and_sharpness(img)
            self.assertIsNotNone(enhanced)
            self.assertEqual(enhanced.mode, "L")  # Grayscale

    def test_binarize_image(self):
        with Image.open(self.input_image) as img:
            binarized = ImagePreprocessor.binarize_image(img, threshold=150)
            self.assertIsNotNone(binarized)
            self.assertEqual(binarized.mode, "1")  # Black & White


if __name__ == "__main__":
    unittest.main()
