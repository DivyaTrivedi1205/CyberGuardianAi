import os
import sys
import csv
import torch
import torch.nn as nn
from collections import defaultdict

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.deepfake_model import EfficientDeepfakeNet

def run_checks():
    print("Running Stage C Verification...")
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    manifest_path = os.path.join(models_dir, 'deepfake_large_experiment_split_manifest.csv')
    
    # Check 1: Artifact preservation
    artifacts = [
        'deepfake_pilot_baseline.pth',
        'deepfake_pilot_baseline_metrics.json',
        'deepfake_pilot3_resumed.pth',
        'deepfake_pilot3_finetuned_metrics.json',
        'deepfake_pilot_experiment_summary.json',
        'deepfake_large_experiment_split_manifest.csv',
        'deepfake_large_experiment_config.json'
    ]
    for art in artifacts:
        p = os.path.join(models_dir, art)
        assert os.path.exists(p), f"Missing artifact: {art}"
    print("Check 1 passed: All artifacts preserved.")
        
    # Check 2: Manifest record counts and balance
    records = []
    split_counts = {'train': {'REAL':0, 'FAKE':0}, 'val': {'REAL':0, 'FAKE':0}, 'test': {'REAL':0, 'FAKE':0}}
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            split_counts[row['split']][row['label']] += 1
            
    assert len(records) == 6000, f"Expected 6000 records, got {len(records)}"
    assert split_counts['train']['REAL'] == 700 and split_counts['train']['FAKE'] == 3500
    assert split_counts['val']['REAL'] == 150 and split_counts['val']['FAKE'] == 750
    assert split_counts['test']['REAL'] == 150 and split_counts['test']['FAKE'] == 750
    print("Check 2 passed: Manifest counts are exactly correct.")
    
    # Check 3: Identity & Split leakage
    # Verify that all original videos and derivatives stay in the same split
    video_to_split = {}
    for r in records:
        path = r['path']
        basename = os.path.basename(path).replace('.mp4', '')
        if '_' in basename:
            a, b = basename.split('_')
            vids = [a, b]
        else:
            vids = [basename]
            
        for vid in vids:
            if vid in video_to_split:
                assert video_to_split[vid] == r['split'], f"Leakage detected for identity {vid}"
            else:
                video_to_split[vid] = r['split']
    print("Check 3 passed: Split integrity and zero leakage confirmed.")
    
    # Check 4: Checkpoint compatibility and save/reload
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = EfficientDeepfakeNet(freeze_backbone=False).to(device)
    
    ckpt_path = os.path.join(models_dir, 'deepfake_pilot3_resumed.pth')
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt['model_state_dict'])
    
    # Test atomic save and reload
    temp_save = os.path.join(models_dir, 'check_temp.pth')
    torch.save({'model_state_dict': model.state_dict()}, temp_save + '.tmp')
    os.replace(temp_save + '.tmp', temp_save)
    reloaded = torch.load(temp_save, map_location=device, weights_only=True)
    os.remove(temp_save)
    print("Check 4 passed: Model loads safely (weights_only=True) and atomic saving works.")
    
    # Check 5: Forward/backward mock test shape check
    inputs = torch.randn(2, 3, 224, 224).to(device)
    labels = torch.tensor([0, 1]).long().to(device)
    criterion = nn.CrossEntropyLoss()
    outputs = model(inputs)
    loss = criterion(outputs, labels)
    loss.backward()
    assert outputs.shape == (2, 2)
    print("Check 5 passed: Lightweight forward/backward passes seamlessly.")
    
    print("Stage C Verification Complete. ALL CHECKS PASSED.")

if __name__ == '__main__':
    run_checks()
