import sys
sys.path.insert(0, '.')
from backend.run_large_experiment import main, setup_logger, run_training
import os

# Monkeypatch epochs and loader limit just to test loop
import backend.run_large_experiment as run_large
import torch

original_dataloader = getattr(run_large, 'DataLoader')

class DummyLoader:
    def __init__(self, orig_loader):
        self.orig = orig_loader
        self.ds = getattr(orig_loader, 'dataset', None)
    def __iter__(self):
        it = iter(self.orig)
        yield next(it)
        yield next(it)
    def __len__(self):
        return 2

def dummy_dataloader(*args, **kwargs):
    loader = original_dataloader(*args, **kwargs)
    return DummyLoader(loader)

setattr(run_large, 'DataLoader', dummy_dataloader)

try:
    run_large.epochs = 1
    run_large.main()
finally:
    lock_file = os.path.join(os.path.dirname(__file__), '..', 'models', '.large_experiment_lock')
    if os.path.exists(lock_file): os.remove(lock_file)
