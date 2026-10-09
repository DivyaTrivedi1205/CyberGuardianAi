import os
import sys
import time
import csv
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
import torchvision.transforms as transforms
import numpy as np
import logging
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score

# Add the project root to sys.path so we can import from backend and services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.dataset_cached import CachedDeepfakeDataset
from services.deepfake_model import EfficientDeepfakeNet

def setup_logger():
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'deepfake_large_experiment_cached.log')

    logger = logging.getLogger('LargeExpCached')
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def evaluate(model, loader, device, logger, split_name="Validation"):
    logger.info(f"--- Running {split_name} ---")
    model.eval()
    all_frame_labels = []
    all_frame_preds = []
    vid_preds_map = {}
    vid_labels_map = {}

    with torch.no_grad():
        for inputs, labels, vid_ids in loader:
            inputs, labels = inputs.to(device), labels.to(device).long()
            outputs = model(inputs)
            if outputs.shape[1] == 2:
                probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
            else:
                probs = torch.sigmoid(outputs).cpu().numpy().flatten()
            preds = (probs >= 0.5).astype(int)

            all_frame_labels.extend(labels.cpu().numpy())
            all_frame_preds.extend(preds)

            for j, v_id in enumerate(vid_ids):
                if v_id not in vid_preds_map:
                    vid_preds_map[v_id] = []
                    vid_labels_map[v_id] = labels[j].item()
                vid_preds_map[v_id].append(probs[j])

    if len(all_frame_preds) == 0:
        return {'vid_f1': 0.0}, [], []

    # Frame metrics
    frame_acc = np.mean(np.array(all_frame_preds) == np.array(all_frame_labels))
    frame_f1 = f1_score(all_frame_labels, all_frame_preds, zero_division=0)

    # Video Metrics
    all_vid_labels = []
    all_vid_preds = []
    all_vid_probs = []

    for v_id, p_list in vid_preds_map.items():
        avg_prob = sum(p_list) / max(1, len(p_list))
        pred = 1 if avg_prob >= 0.5 else 0
        all_vid_labels.append(vid_labels_map[v_id])
        all_vid_preds.append(pred)
        all_vid_probs.append(avg_prob)

    vid_acc = np.mean(np.array(all_vid_preds) == np.array(all_vid_labels))
    vid_prec = precision_score(all_vid_labels, all_vid_preds, zero_division=0)
    vid_rec = recall_score(all_vid_labels, all_vid_preds, zero_division=0)
    vid_f1 = f1_score(all_vid_labels, all_vid_preds, zero_division=0)

    # Handle NaN gracefully for AUC
    try:
        if len(set(all_vid_labels)) > 1:
            vid_auc = roc_auc_score(all_vid_labels, all_vid_probs)
        else:
            vid_auc = 0.0
    except Exception:
        vid_auc = 0.0

    cm = confusion_matrix(all_vid_labels, all_vid_preds).ravel()
    if len(cm) == 4:
        tn, fp, fn, tp = cm
    else:
        tn, fp, fn, tp = 0, 0, 0, 0

    logger.info(f"[{split_name}] Vid Acc: {vid_acc:.4f} | Vid F1: {vid_f1:.4f} | Vid AUC: {vid_auc:.4f}")
    logger.info(f"[{split_name}] CM: TP={tp}, TN={tn}, FP={fp}, FN={fn}")

    metrics = {
        'frame_acc': float(frame_acc), 'frame_f1': float(frame_f1),
        'vid_acc': float(vid_acc), 'vid_precision': float(vid_prec),
        'vid_recall': float(vid_rec), 'vid_f1': float(vid_f1),
        'vid_auc': float(vid_auc),
        'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
        'videos_evaluated': len(all_vid_labels)
    }
    return metrics, all_vid_labels, all_vid_preds

def main():
    logger = setup_logger()
    logger.info("=" * 80)
    logger.info("STARTING CACHED STAGE D: LARGE EXPERIMENT TRAINING")
    logger.info("=" * 80)

    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    lock_file = os.path.join(models_dir, '.large_experiment_lock')

    if os.path.exists(lock_file):
        logger.error(f"Lockfile exists at {lock_file}. Aborting.")
        sys.exit(1)

    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        run_training(logger, models_dir)
    except Exception as e:
        logger.exception(f"Training failed: {e}")
    finally:
        if os.path.exists(lock_file):
            logger.info("Removing lockfile.")
            os.remove(lock_file)

def run_training(logger, models_dir):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")

    manifest_path = os.path.join(models_dir, 'deepfake_large_experiment_split_manifest.csv')
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'deepfake_face_cache')

    # Load manifest
    train_records, val_records, test_records = [], [], []

    with open(manifest_path, 'r') as f:
        for row in csv.DictReader(f):
            rec = {
                'path': row['path'],
                'label': row['label'],
                'split': row['split'],
                'manipulation': row['manipulation'],
                'vid_id': os.path.basename(row['path']).replace('.mp4', '')
            }
            if row['split'] == 'train':
                train_records.append(rec)
            elif row['split'] == 'val':
                val_records.append(rec)
            elif row['split'] == 'test':
                test_records.append(rec)

    logger.info(f"Loaded {len(train_records)} train, {len(val_records)} val, {len(test_records)} test video records.")

    # Create datasets
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = CachedDeepfakeDataset(train_records, cache_dir, transform=train_transform)
    val_ds = CachedDeepfakeDataset(val_records, cache_dir, transform=eval_transform)
    test_ds = CachedDeepfakeDataset(test_records, cache_dir, transform=eval_transform)

    logger.info(f"Train dataset frames: {len(train_ds)}")
    logger.info(f"Val dataset frames: {len(val_ds)}")
    logger.info(f"Test dataset frames: {len(test_ds)}")

    # Calculate weights for sampler from the training dataset frames
    train_labels = [item['label'] for item in train_ds.frames]
    counts = [train_labels.count(0), train_labels.count(1)]
    logger.info(f"Training label counts: REAL={counts[0]}, FAKE={counts[1]}")
    if counts[0] > 0 and counts[1] > 0:
        weights = [1.0 / c for c in counts]
        s_weights = [weights[l] for l in train_labels]
        sampler = WeightedRandomSampler(weights=s_weights, num_samples=len(s_weights), replacement=True)
        shuffle = False
        logger.info("Using WeightedRandomSampler for balancing.")
    else:
        sampler = None
        shuffle = True
        logger.warning("One class missing, using random shuffle.")

    # Batch size can be larger now as we load images from disk directly!
    batch_size = 32
    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, shuffle=shuffle, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size*2, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size*2, shuffle=False, num_workers=0)

    model = EfficientDeepfakeNet(freeze_backbone=False).to(device)

    pilot3_ckpt = os.path.join(models_dir, 'deepfake_pilot3_resumed.pth')
    if os.path.exists(pilot3_ckpt):
        try:
            logger.info(f"Loading initial checkpoint: {pilot3_ckpt}")
            ckpt = torch.load(pilot3_ckpt, map_location=device, weights_only=True)
            model.load_state_dict(ckpt['model_state_dict'])
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam([
        {'params': model.backbone.features.parameters(), 'lr': 1e-4},
        {'params': model.backbone.classifier.parameters(), 'lr': 1e-3}
    ])

    epochs = 5
    best_f1 = 0.0
    best_loss = float('inf')
    history = []
    best_ckpt_path = os.path.join(models_dir, 'deepfake_large_experiment_best.pth')
    metrics_path = os.path.join(models_dir, 'deepfake_large_experiment_metrics.json')

    for epoch in range(epochs):
        logger.info(f"--- Epoch {epoch+1}/{epochs} ---")
        model.train()
        train_loss = 0.0
        start_time = time.time()

        for i, (inputs, labels, _) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device).long()

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            if (i+1) % 50 == 0:
                logger.info(f"  Batch {i+1}/{len(train_loader)} - Loss: {loss.item():.4f}")

        train_loss /= max(1, len(train_loader))
        epoch_time = time.time() - start_time
        logger.info(f"Epoch {epoch+1} Train Loss: {train_loss:.4f} | Time: {epoch_time:.1f}s")

        val_metrics, _, _ = evaluate(model, val_loader, device, logger, split_name="Validation")
        val_metrics['epoch'] = epoch + 1
        val_metrics['train_loss'] = float(train_loss)
        val_metrics['epoch_time_seconds'] = float(epoch_time)
        history.append(val_metrics)

        with open(metrics_path, 'w') as f:
            json.dump({'history': history}, f, indent=4)

        # Select best checkpoint via highest Validation F1
        if val_metrics['vid_f1'] >= best_f1:
            logger.info(f"*** New best Val F1: {val_metrics['vid_f1']:.4f}, saving... ***")
            best_f1 = val_metrics['vid_f1']

            tmp_path = best_ckpt_path + ".tmp"
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_metrics': val_metrics
            }, tmp_path)
            os.replace(tmp_path, best_ckpt_path)

    # Final Evaluation
    logger.info("=" * 80)
    logger.info("FINAL TEST SET EVALUATION")
    logger.info("=" * 80)

    if os.path.exists(best_ckpt_path):
        logger.info(f"Loading best checkpoint for final evaluation...")
        bst_ckpt = torch.load(best_ckpt_path, map_location=device, weights_only=True)
        model.load_state_dict(bst_ckpt['model_state_dict'])
        logger.info(f"Loaded epoch {bst_ckpt.get('epoch')}")

    test_metrics, _, _ = evaluate(model, test_loader, device, logger, split_name="Test")
    test_metrics['stage'] = 'FINAL_TEST'

    final_config_path = os.path.join(models_dir, 'deepfake_large_experiment_config.json')
    if os.path.exists(final_config_path):
        with open(final_config_path, 'r') as f:
            conf = json.load(f)
    else:
        conf = {}

    conf['final_test_metrics'] = test_metrics
    conf['training_history'] = history
    with open(final_config_path, 'w') as f:
        json.dump(conf, f, indent=4)

    logger.info("Experiment completed securely.")

if __name__ == '__main__':
    main()