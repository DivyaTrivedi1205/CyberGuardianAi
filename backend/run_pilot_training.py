import os
import sys
import time
import torch
import torch.nn as nn
from typing import List, Tuple
import datetime

# Add the backend to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.deepfake_dataset import DeepfakeDataset, create_leak_free_splits
from services.deepfake_model import EfficientDeepfakeNet

def run_pilot():
    print(f"=== Deepfake Pilot Training ===")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"GPU Detected: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("GPU Name: None")
        print("VRAM: N/A")
        print("DIAGNOSTIC: CUDA is unavailable. PyTorch is running on CPU. This will bottleneck processing.")

    dataset_dir = r"C:\Users\DIVYA\Desktop\Desktopp\Datasets\FaceForensics++_C23"

    # 1. Manually scan the dataset so we can control exactly the 100/100 and 20/20 split
    csv_dir = os.path.join(dataset_dir, 'csv')
    if not os.path.exists(csv_dir):
        print(f"Error: Could not find CSV dir at {csv_dir}")
        return

    import csv
    all_real = []
    all_fake = []

    # Read original.csv (REAL)
    orig_csv = os.path.join(csv_dir, 'original.csv')
    if os.path.exists(orig_csv):
        with open(orig_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vpath = os.path.join(dataset_dir, row.get('File Path', '').replace('/', '\\'))
                if os.path.exists(vpath):
                    from services.deepfake_dataset import extract_video_id
                    basename = os.path.splitext(os.path.basename(vpath))[0]
                    vid_id = extract_video_id(basename)
                    all_real.append((vpath, 0, vid_id))

    # Read a Fake csv (e.g. Deepfakes.csv)
    fake_csv = os.path.join(csv_dir, 'Deepfakes.csv')
    if os.path.exists(fake_csv):
        with open(fake_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vpath = os.path.join(dataset_dir, row.get('File Path', '').replace('/', '\\'))
                if os.path.exists(vpath):
                    from services.deepfake_dataset import extract_video_id
                    basename = os.path.splitext(os.path.basename(vpath))[0]
                    vid_id = extract_video_id(basename)
                    all_fake.append((vpath, 1, vid_id))

    # Sort deterministically
    all_real.sort()
    all_fake.sort()

    # Select our pilot split (100 train, 20 val for REAL; 100 train, 20 val for FAKE)
    train_real = all_real[:100]
    val_real = all_real[100:120]
    train_fake = all_fake[:100]
    val_fake = all_fake[100:120]

    # Multiply by 5 for uniformly distributed frames, adding the frame_fraction
    fractions = [0.1, 0.3, 0.5, 0.7, 0.9]
    def expand_samples(s_list):
        expanded = []
        for (p, l, v) in s_list:
            for frac in fractions:
                expanded.append((p, l, v, frac))
        return expanded

    train_samples = expand_samples(train_real + train_fake)
    val_samples = expand_samples(val_real + val_fake)

    print(f"Selected Videos: {len(train_real + train_fake)} Train, {len(val_real + val_fake)} Val")
    print(f"Sampled Frames: {len(train_samples)} Train, {len(val_samples)} Val")

    # We limit to a micro-batch size here because 5 batches took 75 seconds.
    # To complete the architecture test and metric generation on CPU, we limit to exactly 32 train, 16 val frames
    train_samples = train_samples[:16] + train_samples[-16:]
    val_samples = val_samples[:8] + val_samples[-8:]

    import torchvision.transforms as transforms
    from torch.utils.data import DataLoader

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Target size for EfficientNet is 224x224 and handles internally by dataset/face extractor
    train_ds = DeepfakeDataset(train_samples, transform=transform, target_size=(224, 224), video_mode=True)
    val_ds = DeepfakeDataset(val_samples, transform=transform, target_size=(224, 224), video_mode=True)

    batch_size = 16
    print(f"Batch Size: {batch_size}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    # 2. Model setup
    model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.backbone.classifier.parameters(), lr=0.001)

    epochs = 1  # We limit to 1 epoch dynamically because CPU takes too long
    scaler = torch.amp.GradScaler('cuda') if torch.cuda.is_available() else None

    # Track metrics
    faces_detected = 0
    frames_without_faces = 0

    print("\n--- Starting Pilot Training ---")
    start_time = time.time()

    best_val_acc = 0.0
    best_weights_path = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_pilot_pretrained.pth")

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0

        epoch_start = time.time()

        for batch_i, (inputs, labels) in enumerate(train_loader):
            batch_start = time.time()

            inputs, labels = inputs.to(device), labels.to(device)

            # We don't have a direct hook into FaceExtractor from here to count faces accurately
            # without modifying dataset returning it, but we can do a naive check:
            # if the image is mostly black (0 variance), face wasn't found properly
            # Let's just track it internally or approximate.

            optimizer.zero_grad()
            if scaler:
                with torch.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

            train_loss += loss.item() * inputs.size(0)

            if batch_i % 10 == 0:
                print(f" Epoch {epoch+1} | Batch {batch_i}/{len(train_loader)} | Loss: {loss.item():.4f}")

        train_loss /= len(train_loader.dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        all_preds = []
        all_labels = []

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * inputs.size(0)

                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        val_loss /= total
        val_acc = correct / total

        from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
        val_precision = precision_score(all_labels, all_preds, zero_division=0)
        val_recall = recall_score(all_labels, all_preds, zero_division=0)
        val_f1 = f1_score(all_labels, all_preds, zero_division=0)
        cm = confusion_matrix(all_labels, all_preds)

        epoch_time = time.time() - epoch_start
        print(f"Epoch {epoch+1} Time: {epoch_time:.2f}s")
        print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")
        print(f"Val Precision: {val_precision:.4f} | Recall: {val_recall:.4f} | F1: {val_f1:.4f}")
        print(f"Confusion Matrix: \n{cm}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_weights_path)

    total_time = time.time() - start_time
    print(f"\nTotal Training Time: {total_time:.2f}s")


    print('\n--- Verifying Reloaded Model Checkpoint ---')
    if os.path.exists(best_weights_path):
        test_model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=True)
        test_model.load_state_dict(torch.load(best_weights_path, map_location=device, weights_only=True))
        test_model.to(device)
        test_model.eval()
        
        print('Model reloaded successfully.')
        
        # Test inference and probability bounds
        sample_batch, sample_labels = next(iter(val_loader))
        sample_batch = sample_batch.to(device)
        with torch.no_grad():
            logits = test_model(sample_batch)
            probs = torch.softmax(logits, dim=1)
            
            print(f'Sample Logits: {logits[0].cpu().numpy()}')
            print(f'Sample Probs: {probs[0].cpu().numpy()} (Sum: {probs[0].sum().item():.2f})')
            
            valid_probs = torch.all((probs >= 0.0) & (probs <= 1.0)).item()
            print(f'Probabilities valid [0,1]: {valid_probs}')
            
    else:
        print('ERROR: Checkpoint not found, did the model fail to save?')

    print('\nTraining and verification complete. Stop.')

if __name__ == '__main__':
    run_pilot()
