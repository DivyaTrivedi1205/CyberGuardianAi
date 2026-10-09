import os
import json
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

class CachedDeepfakeDataset(Dataset):
    def __init__(self, records, cache_dir, transform=None):
        self.samples = records  # list of dicts: path, label, manipulation, split, vid_id
        self.cache_dir = cache_dir
        self.transform = transform
        
        # Build flattened list of actual frames
        self.frames = []
        self.missing_videos = 0
        
        for rec in self.samples:
            vid_id = rec['vid_id']
            manip = rec['manipulation']
            
            meta_path = os.path.join(cache_dir, manip, vid_id, 'metadata.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                
                added = 0
                for f_info in meta.get('frames', []):
                    if f_info['status'] == 'success':
                        self.frames.append({
                            'filepath': os.path.join(cache_dir, manip, vid_id, f_info['file']),
                            'label': 0 if rec['label'] == 'REAL' else 1,
                            'vid_id': vid_id
                        })
                        added += 1
                if added == 0:
                    self.missing_videos += 1
            else:
                self.missing_videos += 1
                
        print(f"Dataset Split loaded. Missing/Failed videos: {self.missing_videos}. Total frames: {len(self.frames)}")

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, idx):
        item = self.frames[idx]
        try:
            img = Image.open(item['filepath']).convert("RGB")
        except:
            img = Image.new("RGB", (224, 224), (0, 0, 0))
            
        if self.transform:
            img_tensor = self.transform(img)
        else:
            default_t = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            img_tensor = default_t(img)
            
        return img_tensor, item['label'], item['vid_id']
