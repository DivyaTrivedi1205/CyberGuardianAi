import torch
import time
import os

print("\n--- CUDA Diagnostics ---")
print(f"Torch Version: {torch.__version__}")
print(f"CUDA Build Version: {torch.version.cuda}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"GPU Total VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
else:
    print("GPU NOT DETECTED. Torch is running strictly as CPU.")
    import sys
    sys.exit(1)

print("\n--- Testing CUDA Tensor Execution ---")
try:
    x = torch.tensor([1.0, 2.0, 3.0], device='cuda')
    y = torch.tensor([4.0, 5.0, 6.0], device='cuda')
    z = x + y
    if z[0].item() == 5.0:
        print("Basic Tensor Addition on CUDA: SUCCESS")
    else:
        print("Basic Tensor Addition on CUDA: LOGIC FAILED")
except Exception as e:
    print(f"Basic Tensor Addition on CUDA: ERROR\n{e}")

print("\n--- GPU Benchmark Routine ---")
try:
    # Need to load model from exactly correct package format
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
    from services.deepfake_model import EfficientDeepfakeNet

    device = torch.device('cuda:0')

    # Tiny efficientnet benchmark
    model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=False).to(device)

    # Dummy tensors on GPU matching format [Batch=4, Channels=3, H=224, W=224] representing frames
    dummy_input = torch.randn(4, 3, 224, 224, device=device)
    dummy_labels = torch.empty(4, dtype=torch.long, device=device).random_(2)

    print(f"Model initialized specifically on: {next(model.parameters()).device}")
    print(f"Dummy Image Input tensor pushed directly to: {dummy_input.device}")

    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print("\nRunning forward pass...")
    t0 = time.time()
    out = model(dummy_input)
    t1 = time.time()
    print(f"Forward pass completed. Output shape: {out.shape}. Processing time: {(t1-t0)*1000:.2f} ms")

    print("Running backward gradient pass...")
    loss = criterion(out, dummy_labels)
    loss.backward()
    optimizer.step()
    t2 = time.time()
    print(f"Backward pass fully executed. Processing time: {(t2-t1)*1000:.2f} ms. No OOM bounds triggered.")

    print("\nFINAL STATUS: Nvidia RTX 4050 processing pipeline actively bound and successfully rendering gradients.")

except Exception as e:
    print(f"\nGPU BENCHMARK FAILURE: {e}")
