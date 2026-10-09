import os
import sys
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
import torchvision.transforms as transforms
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.deepfake_dataset import DeepfakeDataset
from services.deepfake_model import EfficientDeepfakeNet

def test_large_experiment_setup():
    print("="*60)
    print("LIGHTWEIGHT VERIFICATION: LARGE EXPERIMENT")
    print("="*60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # 1. Load manifest
    manifest_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'deepfake_large_experiment_split_manifest.csv')
    dataset_dir = r"C:\Users\DIVYA\Desktop\Desktopp\Datasets\FaceForensics++_C23"

    train_s, val_s, test_s = [], [], []
    train_labels = []

    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Reconstruct absolute paths
            vpath = os.path.join(dataset_dir, row['path'].replace('/', '\\'))
            label_int = 0 if row['label'] == 'REAL' else 1
            # (filepath, label_int, video_id). Note: video_id can just be the basename for tracking
            vid_id = os.path.basename(row['path']).replace('.mp4', '')

            sample = (vpath, label_int, vid_id)
            if row['split'] == 'train':
                train_s.append(sample)
                train_labels.append(label_int)
            elif row['split'] == 'val':
                val_s.append(sample)
            elif row['split'] == 'test':
                test_s.append(sample)

    print(f"Manifest Loaded: Train={len(train_s)}, Val={len(val_s)}, Test={len(test_s)}")

    # 2. WeightedRandomSampler for Train
    class_counts = [train_labels.count(0), train_labels.count(1)]
    weights = [1.0 / count for count in class_counts]
    sample_weights = [weights[label] for label in train_labels]

    sampler = WeightedRandomSampler(weights=sample_weights, num_samples=len(train_labels), replacement=True)

    # Let's take only first 12 videos just to test forward/backward without spending hours
    # Warning: WeightedRandomSampler with small subsets isn't easy, so we'll just slice the samples for the lightweight test
    light_train_s = train_s[:4] + train_s[-4:]

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = DeepfakeDataset(light_train_s, transform=train_transform, video_mode=True, frames_per_video=3) # Reduced to 3 for quick test
    train_loader = DataLoader(train_ds, batch_size=2, shuffle=True)

    # 3. Model init
    model = EfficientDeepfakeNet(freeze_backbone=False).to(device)
    pilot3_ckpt = os.path.join(os.path.dirname(__file__), '..', 'models', 'deepfake_pilot3_resumed.pth')
    print(f"Loading checkpoint {pilot3_ckpt}")
    ckpt = torch.load(pilot3_ckpt, map_location=device, weights_only=True)
    model.load_state_dict(ckpt['model_state_dict'])
    print("Checkpoint loaded safely with weights_only=True")

    # 4. Forward/Backward Test
    criterion = nn.CrossEntropyLoss()
    # Different learning rates for backbone vs classifier
    optimizer = torch.optim.Adam([
        {'params': model.backbone.features.parameters(), 'lr': 1e-4},
        {'params': model.backbone.classifier.parameters(), 'lr': 1e-3}
    ])

    print("\nRunning lightweight forward/backward batch...")
    model.train()

    for i, (inputs, labels) in enumerate(train_loader):
        inputs, labels = inputs.to(device), labels.to(device).long()

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        print(f"Batch {i+1} completed! Loss: {loss.item():.4f}")
        break  # Just test one batch

    print("\nLightweight test passed securely!")

if __name__ == '__main__':
    test_large_experiment_setup()
