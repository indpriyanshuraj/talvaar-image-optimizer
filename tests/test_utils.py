import unittest
import os
import shutil
import tempfile
from resizer_module.utils import get_unique_path, is_ui_texture

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_unique_path_no_conflict(self):
        path = os.path.join(self.test_dir, "test.png")
        self.assertEqual(get_unique_path(path), path)

    def test_get_unique_path_conflict(self):
        path = os.path.join(self.test_dir, "test.png")
        # Create dummy file
        with open(path, 'w') as f:
            f.write("dummy")
        
        expected = os.path.join(self.test_dir, "test_1.png")
        self.assertEqual(get_unique_path(path), expected)

    def test_get_unique_path_multiple_conflicts(self):
        path = os.path.join(self.test_dir, "test.png")
        with open(path, 'w') as f: f.write("dummy")
        with open(os.path.join(self.test_dir, "test_1.png"), 'w') as f: f.write("dummy")
        
        expected = os.path.join(self.test_dir, "test_2.png")
        self.assertEqual(get_unique_path(path), expected)

    def test_is_ui_texture(self):
        self.assertTrue(is_ui_texture("textures/ui/button.png"))
        self.assertTrue(is_ui_texture("textures/gui/container.png"))
        self.assertTrue(is_ui_texture("font/default.png"))
        self.assertTrue(is_ui_texture("colormap/grass.png"))
        
        self.assertFalse(is_ui_texture("textures/blocks/stone.png"))
        self.assertFalse(is_ui_texture("textures/items/apple.png"))
        self.assertTrue(is_ui_texture("C:\\Games\\Minecraft\\textures\\ui\\heart.png")) # Windows path

if __name__ == '__main__':
    unittest.main()
