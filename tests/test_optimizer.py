import unittest
from resizer_module.optimizer import generate_candidates
from resizer_module.analysis import ImageAnalysis

class TestOptimizer(unittest.TestCase):
    def test_candidates_opaque(self):
        analysis = ImageAnalysis(mode="RGB", alpha_type="none", is_ui=False, has_transparency=False)
        candidates = generate_candidates(analysis)
        
        # Expect RGB, P-256, P-128
        self.assertIn(("RGB", None), candidates)
        self.assertIn(("P", 256), candidates)
    
    def test_candidates_binary(self):
        analysis = ImageAnalysis(mode="RGBA", alpha_type="binary", is_ui=False, has_transparency=True)
        candidates = generate_candidates(analysis)
        
        # Expect RGBA, P-256 (P supports binary alpha)
        self.assertIn(("RGBA", None), candidates)
        self.assertIn(("P", 256), candidates)

    def test_candidates_partial(self):
        analysis = ImageAnalysis(mode="RGBA", alpha_type="partial", is_ui=False, has_transparency=True)
        candidates = generate_candidates(analysis)
        
        # Expect ONLY RGBA (P destroys partial alpha)
        self.assertIn(("RGBA", None), candidates)
        self.assertNotIn(("P", 256), candidates)
        
    def test_candidates_ui(self):
        analysis = ImageAnalysis(mode="RGBA", alpha_type="binary", is_ui=True, has_transparency=True)
        candidates = generate_candidates(analysis)
        
        # UI should avoid Palette modes usually
        self.assertIn(("RGBA", None), candidates)
        self.assertNotIn(("P", 256), candidates)

    def test_ignore_transparency(self):
        # Even if partial alpha, if we ignore it, we should get RGB/Palette options
        analysis = ImageAnalysis(mode="RGBA", alpha_type="partial", is_ui=False, has_transparency=True)
        candidates = generate_candidates(analysis, ignore_transparency=True)
        
        self.assertIn(("RGB", None), candidates)
        self.assertIn(("P", 256), candidates)

if __name__ == '__main__':
    unittest.main()
