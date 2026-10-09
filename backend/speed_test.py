import os, sys, time, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.deepfake_dataset import DeepfakeDataset
from torch.utils.data import DataLoader
import torchvision.transforms as transforms

if __name__ == '__main__':
    manifest_path = 'models/deepfake_large_experiment_split_manifest.csv'
    import csv
    train_samples = []
    dataset_dir = "C:/Users/DIVYA/Desktop/Desktopp/Datasets/FaceForensics++_C23"
    with open(manifest_path, 'r') as f:
        for r in csv.DictReader(f):
            if r['split'] == 'train':
                vpath = os.path.join(dataset_dir, r['path'].replace('\', '/'))
                for fr in [0.1, 0.5, 0.9]:
                    train_samples.append((vpath, 0 if r['label'] == 'REAL' else 1, r['path'], fr))
                if len(train_samples) > 200: break
                
    transform = transforms.Compose([transforms.Resize((224,224)), transforms.ToTensor()])
    ds = DeepfakeDataset(train_samples, transform=transform, video_mode=True)
    
    for nw in [0, 2, 4]:
        dl = DataLoader(ds, batch_size=32, num_workers=nw, shuffle=True)
        t0 = time.time()
        for i, b in enumerate(dl):
            if i >= 1: break
        print(f"num_workers={nw}, batch_size=32 -> time for 2 batches: {time.time()-t0:.2f}s")
