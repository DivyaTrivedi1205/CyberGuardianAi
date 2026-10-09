import os
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
import csv
from datetime import datetime
import json
import collections

# Add the backend to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.deepfake_dataset import DeepfakeDataset, extract_video_id
from services.deepfake_model import EfficientDeepfakeNet

def format_time(seconds):
    """Format time in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds//60)}m {int(seconds%60)}s"
    else:
        return f"{int(seconds//3600)}h {int((seconds%60)//60)}m"

class ValDatasetWithVideoID(DeepfakeDataset):
    """Wrapper that returns video_id in addition to img and label."""
    def __getitem__(self, idx):
        img_tensor, label = super().__getitem__(idx)
        video_id = self.samples[idx][2]
        return img_tensor, label, video_id

def run_pilot_resume():
    print("=" * 80)
    print("DEEPFAKE PILOT 3 RESUME - FINE-TUNING EFFICIENTNET-B0")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    checkpoint_path = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_pilot3_finetuned.pth")
    metrics_path = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_pilot3_finetuned_metrics.json")
    resume_checkpoint_path = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_pilot3_resumed.pth")
    lockfile_path = os.path.join(os.path.dirname(__file__), "..", "models", ".pilot3_resume_lock")

    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

    if os.path.exists(lockfile_path):
        print(f"ERROR: Lockfile exists at {lockfile_path}.")
        print("Another pilot3 resume process might be running. Aborting.")
        return

    try:
        with open(lockfile_path, "w") as f:
            f.write(str(os.getpid()))

        _run_pilot_resume_inner(checkpoint_path, metrics_path, resume_checkpoint_path)
    finally:
        if os.path.exists(lockfile_path):
            os.remove(lockfile_path)

def _run_pilot_resume_inner(checkpoint_path, metrics_path, resume_checkpoint_path):
    # ============ 1. ENVIRONMENT DIAGNOSTICS ============
    print("\n[1] ENVIRONMENT DIAGNOSTICS")
    print("-" * 40)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"PyTorch Version: {torch.__version__}")
    print(f"Device: {device}")

    if torch.cuda.is_available():
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        torch.cuda.empty_cache()
        print(f"Initial GPU Memory Allocated: {torch.cuda.memory_allocated() / 1024**3:.3f} GB")
    else:
        print("ERROR: CUDA not available!")
        return

    # ============ 2. LOAD EXISTING PILOT 3 CHECKPOINT ============
    print("\n[2] LOADING PILOT 3 CHECKPOINT FOR RESUME")
    print("-" * 40)

    assert os.path.exists(checkpoint_path), f"Pilot 3 checkpoint not found at {checkpoint_path}"
    print(f"Loading checkpoint: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)

    print(f"Checkpoint loaded successfully with weights_only=True")
    print(f"  Epoch: {checkpoint['epoch']}")
    print(f"  Video F1: {checkpoint['vid_f1']:.4f}")
    print(f"  Video Acc: {checkpoint['vid_acc']:.4f}")
    print(f"  Video AUC: {checkpoint['vid_auc']:.4f}")

    # Extract history from checkpoint
    history = checkpoint.get('history', {})

    # ============ 3. DATASET PREPARATION ============
    print("\n[3] DATASET PREPARATION")
    print("-" * 40)

    dataset_dir = r"C:\Users\DIVYA\Desktop\Desktopp\Datasets\FaceForensics++_C23"
    csv_dir = os.path.join(dataset_dir, 'csv')

    if not os.path.exists(csv_dir):
        print(f"ERROR: CSV directory not found at {csv_dir}")
        return

    all_real = []
    all_fake = []

    orig_csv = os.path.join(csv_dir, 'original.csv')
    if os.path.exists(orig_csv):
        with open(orig_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vpath = os.path.join(dataset_dir, row.get('File Path', '').replace('/', '\\'))
                if os.path.exists(vpath):
                    vid_id = extract_video_id(os.path.basename(vpath))
                    all_real.append((vpath, 0, vid_id))
    print(f"Found {len(all_real)} REAL videos")

    fake_csv = os.path.join(csv_dir, 'Deepfakes.csv')
    if os.path.exists(fake_csv):
        with open(fake_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vpath = os.path.join(dataset_dir, row.get('File Path', '').replace('/', '\\'))
                if os.path.exists(vpath):
                    vid_id = extract_video_id(os.path.basename(vpath))
                    all_fake.append((vpath, 1, vid_id))
    print(f"Found {len(all_fake)} FAKE videos")

    all_real.sort()
    all_fake.sort()

    train_real = all_real[:100]
    val_real = all_real[100:120]
    train_fake = all_fake[:100]
    val_fake = all_fake[100:120]

    print(f"\nPilot Split:")
    print(f"  Training: {len(train_real)} REAL + {len(train_fake)} FAKE = {len(train_real) + len(train_fake)} videos")
    print(f"  Validation: {len(val_real)} REAL + {len(val_fake)} FAKE = {len(val_real) + len(val_fake)} videos")

    fractions = [0.1, 0.3, 0.5, 0.7, 0.9]

    def expand_samples(s_list):
        expanded = []
        for (p, l, v) in s_list:
            for frac in fractions:
                expanded.append((p, l, v, frac))
        return expanded

    train_samples = expand_samples(train_real + train_fake)
    val_samples = expand_samples(val_real + val_fake)

    total_train_frames = len(train_samples)
    total_val_frames = len(val_samples)

    print(f"\nFrame Sampling (5 frames/video):")
    print(f"  Training frames: {total_train_frames}")
    print(f"  Validation frames: {total_val_frames}")
    print(f"  Total pilot frames: {total_train_frames + total_val_frames}")

    # ============ 4. DATA LOADERS WITH AUGMENTATION ============
    print("\n[4] DATA LOADERS WITH AUGMENTATION")
    print("-" * 40)

    train_transform = transforms.Compose([
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(
            brightness=0.15,
            contrast=0.15,
            saturation=0.10,
            hue=0.02
        ),
        transforms.RandomAffine(
            degrees=5,
            translate=(0.03, 0.03),
            scale=(0.97, 1.03)
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = DeepfakeDataset(
        train_samples,
        transform=train_transform,
        target_size=(224, 224),
        video_mode=True
    )
    val_ds = ValDatasetWithVideoID(
        val_samples,
        transform=val_transform,
        target_size=(224, 224),
        video_mode=True
    )

    batch_size = 16
    num_workers = 0

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    print(f"Batch size: {batch_size}")
    print(f"Num workers: {num_workers} (Windows-safe)")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")

    # ============ 5. MODEL SETUP WITH PARTIAL UNFREEZING ============
    print("\n[5] MODEL SETUP - PARTIAL EFFICIENTNET-B0 UNFREEZING")
    print("-" * 40)

    # Create model and load from checkpoint
    model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=False)
    model = model.to(device)

    # Setup model with proper freeze configuration BEFORE loading optimizer state
    # Freeze everything first
    for param in model.backbone.parameters():
        param.requires_grad = False

    # Unfreeze features.8 (last conv block) and classifier
    for name, param in model.backbone.named_parameters():
        if name.startswith('features.8.') or name.startswith('classifier.'):
            param.requires_grad = True

    model.load_state_dict(checkpoint['model_state_dict'])
    print("Pilot 3 model state dict loaded successfully.")

    # Verify trainable parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = total_params - trainable_params

    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    print(f"Frozen parameters: {frozen_params:,}")

    # Create parameter groups for discriminative learning rates
    features_8_params = []
    classifier_params = []

    for name, param in model.named_parameters():
        if param.requires_grad:
            if name.startswith('backbone.features.8.'):
                features_8_params.append(param)
            else:
                classifier_params.append(param)

    optimizer = torch.optim.Adam([
        {'params': features_8_params, 'lr': 1e-4},
        {'params': classifier_params, 'lr': 1e-3}
    ])

    # Load optimizer state if present
    if 'optimizer_state_dict' in checkpoint:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        # Move optimizer state to GPU
        for state in optimizer.state.values():
            for k, v in state.items():
                if isinstance(v, torch.Tensor):
                    state[k] = v.to(device)
        print("Optimizer state dict loaded.")
    else:
        print("WARNING: No optimizer state in checkpoint - starting fresh optimizer state.")

    # Initialize scheduler (NOT resuming from checkpoint - scheduler not saved)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='max',
        factor=0.5,
        patience=2,
        verbose=False,
        min_lr=1e-6
    )
    print("NOTE: Scheduler state not loaded (not saved in checkpoint). Starting fresh scheduler.")

    print(f"Using full float32 (no AMP)")

    # ============ 6. RESUME CONFIGURATION ============
    print("\n[6] RESUME CONFIGURATION")
    print("-" * 40)
    epochs = 5
    start_epoch = checkpoint['epoch']  # This is 2, so we start at epoch 3
    print(f"Resuming from Epoch: {start_epoch}")
    print(f"Target Epochs: {epochs}")
    print(f"Remaining epochs to train: {epochs - start_epoch}")
    print(f"Optimizer: Adam (lr=1e-3 for head, 1e-4 for features.8)")
    print(f"LR Scheduler: ReduceLROnPlateau (factor=0.5, patience=2, min_lr=1e-6) [fresh, not resumed]")
    print(f"Loss: CrossEntropyLoss")
    print(f"Backbone: EfficientNet-B0 (frozen features.0-7, unfrozen features.8 + classifier)")

    # ============ 7. RESUME TRAINING LOOP ============
    print("\n[7] RESUMING TRAINING LOOP")
    print("-" * 40)

    best_vid_f1 = checkpoint.get('vid_f1', 0.0)
    best_epoch = checkpoint['epoch']  # Epoch that had best metrics
    print(f"Best Video F1 from checkpoint: {best_vid_f1:.4f} (Epoch {best_epoch})")

    # Restore history from checkpoint
    if history:
        print(f"History restored from checkpoint ({len(history['vid_f1'])} epochs)")
    else:
        history = {
            'train_loss': [], 'val_loss': [],
            'frame_acc': [], 'frame_f1': [],
            'vid_acc': [], 'vid_precision': [], 'vid_recall': [], 'vid_f1': [], 'vid_auc': [],
            'epoch_time': []
        }

    total_start_time = time.time()

    for epoch in range(start_epoch, epochs):
        epoch_start = time.time()

        model.train()
        train_loss = 0.0
        train_batches = 0

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            # Debug: check model and input devices
            if batch_idx == 0 and epoch == start_epoch:
                print(f"  Debug: inputs.device={inputs.device}, labels.device={labels.device}")
                print(f"  Debug: model.parameters() devices: {[p.device for p in model.parameters()]}")

            inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)

            optimizer.zero_grad()

            outputs = model(inputs)
            loss = nn.CrossEntropyLoss()(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            train_batches += inputs.size(0)

            if (batch_idx + 1) % 20 == 0:
                print(f"  Epoch {epoch+1}/{epochs} | Batch {batch_idx+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

        train_loss /= train_batches

        model.eval()
        val_loss = 0.0
        val_total = 0

        vid_preds_map = collections.defaultdict(list)
        vid_labels_map = {}

        all_frame_preds = []
        all_frame_labels = []

        with torch.no_grad():
            for inputs, labels, vids in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)

                outputs = model(inputs)
                loss = nn.CrossEntropyLoss()(outputs, labels)

                val_loss += loss.item() * inputs.size(0)

                probs = torch.softmax(outputs, dim=1)
                _, predicted = torch.max(outputs, 1)

                val_total += labels.size(0)

                for i in range(len(vids)):
                    vid_id = vids[i]
                    p_fake = probs[i, 1].item()
                    lbl = labels[i].item()
                    vid_preds_map[vid_id].append(p_fake)
                    vid_labels_map[vid_id] = lbl

                all_frame_preds.extend(predicted.cpu().numpy())
                all_frame_labels.extend(labels.cpu().numpy())

        val_loss /= val_total

        frame_acc = np.mean(np.array(all_frame_preds) == np.array(all_frame_labels))
        frame_f1 = f1_score(all_frame_labels, all_frame_preds, zero_division=0)

        all_vid_labels = []
        all_vid_preds = []
        all_vid_probs = []

        for vid, p_list in vid_preds_map.items():
            avg_prob = sum(p_list) / len(p_list)
            pred = 1 if avg_prob >= 0.5 else 0
            all_vid_labels.append(vid_labels_map[vid])
            all_vid_preds.append(pred)
            all_vid_probs.append(avg_prob)

        vid_acc = np.mean(np.array(all_vid_preds) == np.array(all_vid_labels))
        vid_precision = precision_score(all_vid_labels, all_vid_preds, zero_division=0)
        vid_recall = recall_score(all_vid_labels, all_vid_preds, zero_division=0)
        vid_f1 = f1_score(all_vid_labels, all_vid_preds, zero_division=0)
        cm = confusion_matrix(all_vid_labels, all_vid_preds)

        try:
            vid_auc = roc_auc_score(all_vid_labels, all_vid_probs)
        except:
            vid_auc = float('nan')

        epoch_time = time.time() - epoch_start

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['frame_acc'].append(float(frame_acc))
        history['frame_f1'].append(float(frame_f1))
        history['vid_acc'].append(float(vid_acc))
        history['vid_precision'].append(float(vid_precision))
        history['vid_recall'].append(float(vid_recall))
        history['vid_f1'].append(float(vid_f1))
        history['vid_auc'].append(float(vid_auc))
        history['epoch_time'].append(float(epoch_time))

        print(f"\nEpoch {epoch+1}/{epochs} Summary:")
        print(f"  Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
        print(f"  [Frame-level] Accuracy: {frame_acc:.4f}, F1: {frame_f1:.4f}")
        print(f"  [Video-level] Accuracy: {vid_acc:.4f} ({sum(np.array(all_vid_preds) == np.array(all_vid_labels))}/{len(all_vid_labels)})")
        print(f"                Precision: {vid_precision:.4f}, Recall: {vid_recall:.4f}")
        print(f"                F1: {vid_f1:.4f}, AUC: {vid_auc:.4f}")
        print(f"                Confusion Matrix: TP={cm[1,1]}, TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}")
        print(f"  Epoch Time: {format_time(epoch_time)}")

        scheduler.step(vid_f1)

        with open(metrics_path, 'w') as f:
            json.dump(history, f, indent=4)

        # Save checkpoint for this epoch
        if vid_f1 > best_vid_f1:
            best_vid_f1 = vid_f1
            best_epoch = epoch + 1

            # Save to separate file first to preserve original
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'vid_f1': float(vid_f1),
                'vid_acc': float(vid_acc),
                'vid_auc': float(vid_auc),
                'vid_precision': float(vid_precision),
                'vid_recall': float(vid_recall),
                'history': {k: [float(x) for x in v] for k, v in history.items()}
            }, resume_checkpoint_path)

            print(f"  *** New best model saved (Video Val F1: {vid_f1:.4f}) ***")

    total_time = time.time() - total_start_time

    # ============ 8. FINAL RESULTS ============
    print("\n" + "=" * 80)
    print("PILOT 3 RESUME RESULTS")
    print("=" * 80)

    print(f"\nBest Model (Epoch {best_epoch}):")
    print(f"  Video Validation F1: {best_vid_f1:.4f}")
    print(f"  Video Validation Accuracy: {history['vid_acc'][best_epoch-1]:.4f}")
    print(f"  Video Validation Precision: {history['vid_precision'][best_epoch-1]:.4f}")
    print(f"  Video Validation Recall: {history['vid_recall'][best_epoch-1]:.4f}")
    print(f"  Video Validation AUC: {history['vid_auc'][best_epoch-1]:.4f}")

    print(f"\nTraining Statistics:")
    print(f"  Batch Size: {batch_size}")
    print(f"  Total Training Time: {format_time(total_time)}")
    print(f"  Average Epoch Time: {format_time(np.mean(history['epoch_time']))}")

    print(f"\nParameter Statistics:")
    print(f"  Total Parameters: {total_params:,}")
    print(f"  Trainable Parameters: {trainable_params:,}")
    print(f"  Frozen Parameters: {frozen_params:,}")

    print(f"\nGPU Memory:")
    if torch.cuda.is_available():
        print(f"  Peak Memory Allocated: {torch.cuda.max_memory_allocated() / 1024**3:.3f} GB")

    # ============ 9. MODEL RELOAD AND VERIFICATION ============
    print("\n[9] MODEL RELOAD AND VERIFICATION")
    print("-" * 40)

    if os.path.exists(resume_checkpoint_path):
        print(f"Loading resume checkpoint: {resume_checkpoint_path}")

        test_model = EfficientDeepfakeNet(num_classes=2, freeze_backbone=False)
        test_model = test_model.to(device)

        checkpoint = torch.load(resume_checkpoint_path, map_location=device, weights_only=True)
        test_model.load_state_dict(checkpoint['model_state_dict'])
        test_model.eval()

        print("Resume model reloaded successfully with weights_only=True")

        ckpt_trainable = sum(p.numel() for p in test_model.parameters() if p.requires_grad)
        print(f"  Reloaded model trainable params: {ckpt_trainable:,} (expected: {trainable_params:,})")

        if abs(ckpt_trainable - trainable_params) > 1000:
            print(f"  WARNING: Parameter count mismatch!")
    else:
        print("ERROR: Resume checkpoint not found!")

    # ============ 10. GPU CLEANUP ============
    print("\n[10] CLEANUP")
    print("-" * 40)
    torch.cuda.empty_cache()
    print("GPU cache cleared.")

    print(f"\nResume checkpoint saved to: {resume_checkpoint_path}")
    print(f"Metrics saved to: {metrics_path}")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ============ 11. COMPARISON WITH PILOT 2 ============
    print("\n" + "=" * 80)
    print("PILOT 3 vs PILOT 2 COMPARISON")
    print("=" * 80)

    # Load Pilot 2 metrics for comparison
    pilot2_metrics = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_pilot_baseline_metrics.json")
    with open(pilot2_metrics, 'r') as f:
        pilot2_history = json.load(f)

    # Find best epoch for comparison
    best_pilot2_epoch = pilot2_history['vid_f1'].index(max(pilot2_history['vid_f1']))

    print(f"\nPilot 2 Baseline (Best Epoch {best_pilot2_epoch + 1}):")
    print(f"  Video Accuracy: {pilot2_history['vid_acc'][best_pilot2_epoch]:.4f}")
    print(f"  Video F1: {pilot2_history['vid_f1'][best_pilot2_epoch]:.4f}")
    print(f"  Video AUC: {pilot2_history['vid_auc'][best_pilot2_epoch]:.4f}")

    # Get Pilot 3 best metrics
    pilot3_best_idx = best_epoch - 1
    print(f"\nPilot 3 Resume (Epoch {best_epoch}):")
    print(f"  Video Accuracy: {history['vid_acc'][pilot3_best_idx]:.4f}")
    print(f"  Video F1: {history['vid_f1'][pilot3_best_idx]:.4f}")
    print(f"  Video AUC: {history['vid_auc'][pilot3_best_idx]:.4f}")

    acc_improvement = history['vid_acc'][pilot3_best_idx] - pilot2_history['vid_acc'][best_pilot2_epoch]
    f1_improvement = history['vid_f1'][pilot3_best_idx] - pilot2_history['vid_f1'][best_pilot2_epoch]
    auc_improvement = history['vid_auc'][pilot3_best_idx] - pilot2_history['vid_auc'][best_pilot2_epoch]

    print(f"\nImprovement vs Pilot 2:")
    print(f"  Accuracy: {acc_improvement:+.4f}")
    print(f"  F1: {f1_improvement:+.4f}")
    print(f"  AUC: {auc_improvement:+.4f}")

    if acc_improvement > 0 and f1_improvement > 0:
        print(f"\nRESULT: Pilot 3 IMPROVED over Pilot 2 baseline!")
    elif acc_improvement < 0 and f1_improvement < 0:
        print(f"\nRESULT: Pilot 3 WORSENED compared to Pilot 2 baseline.")
    else:
        print(f"\nRESULT: Pilot 3 showed mixed results vs Pilot 2 baseline.")

    print("\n" + "=" * 80)
    print("PILOT 3 RESUME COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    run_pilot_resume()
