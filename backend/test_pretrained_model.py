import os
import sys
import unittest
import torch
import torch.nn as nn
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.deepfake_model import EfficientDeepfakeNet, LegacyDeepfakeCNN
from services.deepfake_analyzer import get_cnn_model, analyze_deepfake

class TestPriority2Model(unittest.TestCase):

    def test_model_construction(self):
        """Test EfficientNet-B0 construction and head replacement setup."""
        model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=True)
        self.assertIsInstance(model, nn.Module)

        # Verify backbone classifier head was actually replaced
        # Original EfficientNet B0 has out_features=1000, ours is 2
        classifier = model.backbone.classifier
        self.assertEqual(classifier[-1].out_features, 2)

        total_params = sum(p.numel() for p in model.parameters())
        print(f"\\nEfficientDeepfakeNet Params: {total_params:,}")
        self.assertGreater(total_params, 4_000_000) # Should be ~4M to 5M parameters
        self.assertLess(total_params, 10_000_000)

    def test_forward_pass_cpu(self):
        """Test CPU inference forward pass."""
        model = EfficientDeepfakeNet()
        model.eval()

        # Representative tensor size for EfficientNet (B, C, H, W)
        dummy_input = torch.randn(1, 3, 224, 224)

        with torch.no_grad():
            output = model(dummy_input)

        self.assertEqual(output.shape, (1, 2))

    def test_forward_pass_gpu_if_available(self):
        """Test GPU inference forward pass if CUDA is available."""
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available, skipping GPU inference test")

        model = EfficientDeepfakeNet()
        model.to('cuda')
        model.eval()

        dummy_input = torch.randn(1, 3, 224, 224).to('cuda')

        with torch.no_grad():
            output = model(dummy_input)

        self.assertEqual(output.shape, (1, 2))

    def test_checkpoint_save_and_load(self):
        """Test saving and loading custom state_dict correctly."""
        model = EfficientDeepfakeNet()

        # Modify a weight slightly to verify reload
        with torch.no_grad():
            model.backbone.classifier[-1].weight[0, 0] = 9.99

        import tempfile
        temp = tempfile.NamedTemporaryFile(delete=False)
        path = temp.name
        temp.close()

        try:
            torch.save(model.state_dict(), path)

            # Load into fresh model
            new_model = EfficientDeepfakeNet()
            state_dict = torch.load(path, weights_only=True)
            new_model.load_state_dict(state_dict)

            self.assertAlmostEqual(new_model.backbone.classifier[-1].weight[0, 0].item(), 9.99, places=2)
        finally:
            os.unlink(path)

    def test_api_backward_compatibility(self):
        """Test that the updated inference pipeline defaults correctly without failing."""
        # This will trigger get_cnn_model() inside analyze_deepfake
        # which should safely fall back to the Legacy model if the priority2 file is absent.
        import io
        img = Image.new('RGB', (128, 128), (200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        try:
            res = analyze_deepfake(buf.getvalue(), "test_fallback.jpeg", "image/jpeg")
            self.assertIn("prediction", res)
            self.assertIn("risk_score", res)
        except Exception as e:
            self.fail(f"API pipeline compatibility broken: {e}")

if __name__ == '__main__':
    unittest.main()
