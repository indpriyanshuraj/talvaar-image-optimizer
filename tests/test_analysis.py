import unittest
from PIL import Image
from resizer_module.analysis import analyze_image

class TestAnalysis(unittest.TestCase):
    def test_opaque_image(self):
        # Create solid red image
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        analysis = analyze_image(img, "test.png")
        
        self.assertEqual(analysis.alpha_type, "none")
        self.assertFalse(analysis.has_transparency)
        # Suggested algorithm for solid color should be NEAREST (low color count)
        self.assertEqual(analysis.suggested_algorithm, "NEAREST")

    def test_binary_transparency(self):
        # Create image with solid pixels and full transparent pixels
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        # Draw some solid pixels
        for x in range(5):
            img.putpixel((x, 0), (255, 0, 0, 255))
            
        analysis = analyze_image(img, "test.png")
        self.assertEqual(analysis.alpha_type, "binary")
        self.assertTrue(analysis.has_transparency)
        self.assertEqual(analysis.suggested_algorithm, "NEAREST")

    def test_partial_transparency(self):
        # Create image with semi-transparent pixels
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        img.putpixel((5, 5), (255, 0, 0, 128)) # 50% opacity
        
        analysis = analyze_image(img, "test.png")
        self.assertEqual(analysis.alpha_type, "partial")
        self.assertTrue(analysis.has_transparency)
        # Suggestion depends on logic, likely NEAREST if color count is low, but usually we just care about alpha here
        
    def test_ui_context(self):
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        # Force high color count noise
        import random
        for x in range(100):
            for y in range(100):
                img.putpixel((x,y), (random.randint(0,255), random.randint(0,255), random.randint(0,255)))
                
        analysis = analyze_image(img, "path/to/ui/background.png")
        self.assertTrue(analysis.is_ui)
        self.assertEqual(analysis.suggested_algorithm, "NEAREST")

if __name__ == '__main__':
    unittest.main()
