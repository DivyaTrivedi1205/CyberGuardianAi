import torch
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.deepfake_dataset import DeepfakeDataset
from torch.utils.data import DataLoader

if __name__ == '__main__':
    ds = DeepfakeDataset([("C:/Users/DIVYA/Desktop/Desktopp/Datasets/FaceForensics++_C23/original/000.mp4", 0, "000")], video_mode=True, frames_per_video=5)
    dl = DataLoader(ds, batch_size=1, num_workers=4)
    import time
    t0 = time.time()
    for b in dl: pass
    print("Time:", time.time() - t0)
