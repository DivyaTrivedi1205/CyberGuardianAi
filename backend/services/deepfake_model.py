import os
import io
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import laplace
from sklearn.ensemble import RandomForestClassifier

# Synthetic image generator helper for training
def generate_synthetic_image_bytes(is_fake: bool) -> bytes:
    # Base canvas
    arr = np.zeros((128, 128, 3), dtype=np.uint8)
    
    # Generate background patterns
    r_grad = np.tile(np.linspace(np.random.randint(40, 90), np.random.randint(160, 220), 128), (128, 1)).T
    g_grad = np.tile(np.linspace(np.random.randint(40, 90), np.random.randint(160, 220), 128), (128, 1))
    b_grad = np.ones((128, 128)) * np.random.randint(90, 170)
    arr[:, :, 0] = r_grad.astype(np.uint8)
    arr[:, :, 1] = g_grad.astype(np.uint8)
    arr[:, :, 2] = b_grad.astype(np.uint8)
    
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    
    # Draw subject elements
    draw.ellipse([25, 25, 102, 102], fill=(np.random.randint(120, 255), np.random.randint(120, 255), np.random.randint(120, 255)))
    draw.rectangle([45, 45, 82, 82], fill=(np.random.randint(40, 140), np.random.randint(40, 140), np.random.randint(40, 140)))
    
    pixels = np.array(img).astype(np.float32)
    
    if is_fake:
        # Add AI artifacts:
        # 1. Periodic grid lines representing transposed conv/upsampling
        x_grid = np.linspace(0, 2 * np.pi, 128)
        y_grid = np.linspace(0, 2 * np.pi, 128)
        xx, yy = np.meshgrid(x_grid, y_grid)
        grid = np.sin(xx * 32) * np.sin(yy * 32) * 16.0  # high frequency wave
        for c in range(3):
            pixels[:, :, c] += grid
            
        # 2. Localized noise variance mismatch (simulating deepfake face swap patch)
        center_noise = np.random.normal(0, 12.0, (44, 44, 3))
        pixels[42:86, 42:86, :] += center_noise
        
        # 3. Localized blur / blending boundary
        patch = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
        box = (38, 38, 90, 90)
        cropped = patch.crop(box)
        blurred = cropped.filter(ImageFilter.GaussianBlur(radius=2.0))
        patch.paste(blurred, box)
        pixels = np.array(patch).astype(np.float32)
    else:
        # Authentic: homogeneous camera sensor noise across the image
        sensor_noise = np.random.normal(0, 4.0, (128, 128, 3))
        pixels += sensor_noise
        
    final_arr = np.clip(pixels, 0, 255).astype(np.uint8)
    final_img = Image.fromarray(final_arr)
    
    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

def extract_forensics_features(img: Image.Image) -> np.ndarray:
    # 1. Resize and convert for FFT and noise analysis
    img_gray = img.convert("L")
    img_gray_256 = np.array(img_gray.resize((256, 256)))
    
    # 2. FFT Features
    f = np.fft.fft2(img_gray_256)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    
    # Compute radial profile
    y, x = np.indices(magnitude.shape)
    cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
    r = np.sqrt((x - cx)**2 + (y - cy)**2)
    r = r.astype(int)
    
    tbin = np.bincount(r.ravel(), magnitude.ravel())
    nr = np.bincount(r.ravel())
    radial_profile = tbin / (nr + 1e-6)
    
    # Downsample radial profile to exactly 8 bins
    fft_radial_bins = []
    bin_size = len(radial_profile) // 8
    for i in range(8):
        bin_vals = radial_profile[i*bin_size:(i+1)*bin_size]
        fft_radial_bins.append(np.mean(bin_vals) if len(bin_vals) > 0 else 0.0)
        
    # FFT PAPR of high frequencies
    high_freq_vals = magnitude[r > 90]
    papr = np.max(high_freq_vals) / (np.mean(high_freq_vals) + 1e-6) if len(high_freq_vals) > 0 else 1.0
    
    # 3. Noise Features (Laplacian)
    res = laplace(img_gray_256.astype(np.float32))
    h, w = res.shape
    block_h, block_w = h // 8, w // 8
    noise_variances = []
    for i in range(8):
        for j in range(8):
            block = res[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
            noise_variances.append(np.var(block))
    noise_variances = np.array(noise_variances)
    noise_mean = np.mean(noise_variances)
    noise_std = np.std(noise_variances)
    noise_inconsistency = noise_std / (noise_mean + 1e-6)
    
    # 4. Error Level Analysis (ELA)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    compressed_img = Image.open(buf)
    orig_arr = np.array(img.convert("RGB")).astype(np.float32)
    comp_arr = np.array(compressed_img).astype(np.float32)
    diff = np.abs(orig_arr - comp_arr)
    diff_gray = np.mean(diff, axis=2)
    diff_gray_resized = np.array(Image.fromarray(diff_gray.astype(np.uint8)).resize((256, 256)))
    
    h, w = diff_gray_resized.shape
    block_h, block_w = h // 8, w // 8
    ela_variances = []
    for i in range(8):
        for j in range(8):
            block = diff_gray_resized[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
            ela_variances.append(np.var(block))
    ela_variances = np.array(ela_variances)
    ela_mean = np.mean(ela_variances)
    ela_std = np.std(ela_variances)
    ela_inconsistency = ela_std / (ela_mean + 1e-6)
    
    # 5. Channel Correlations
    img_arr = np.array(img).astype(np.float32)
    r_chan = img_arr[:, :, 0].ravel()
    g_chan = img_arr[:, :, 1].ravel()
    b_chan = img_arr[:, :, 2].ravel()
    if len(r_chan) <= 1 or np.std(r_chan) == 0 or np.std(g_chan) == 0 or np.std(b_chan) == 0:
        mean_corr = 1.0
        min_corr = 1.0
    else:
        corr_rg = np.corrcoef(r_chan, g_chan)[0, 1]
        corr_gb = np.corrcoef(g_chan, b_chan)[0, 1]
        corr_br = np.corrcoef(b_chan, r_chan)[0, 1]
        corr_rg = 1.0 if np.isnan(corr_rg) else corr_rg
        corr_gb = 1.0 if np.isnan(corr_gb) else corr_gb
        corr_br = 1.0 if np.isnan(corr_br) else corr_br
        mean_corr = (corr_rg + corr_gb + corr_br) / 3.0
        min_corr = min(corr_rg, corr_gb, corr_br)
        
    features = [
        *fft_radial_bins,
        float(papr),
        float(noise_inconsistency),
        float(noise_mean),
        float(ela_inconsistency),
        float(ela_mean),
        float(mean_corr),
        float(min_corr)
    ]
    return np.array(features, dtype=np.float32)

def train_deepfake_model(dataset_path=None) -> str:
    print("Initializing Deepfake Random Forest training...")
    
    X = []
    y = []
    
    # Load custom dataset if provided
    loaded_custom = False
    if dataset_path and os.path.exists(dataset_path):
        print(f"Loading custom dataset from: {dataset_path}")
        real_dir = os.path.join(dataset_path, "real")
        fake_dir = os.path.join(dataset_path, "fake")
        
        if os.path.exists(real_dir):
            for f in os.listdir(real_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    try:
                        img = Image.open(os.path.join(real_dir, f)).convert("RGB")
                        feats = extract_forensics_features(img)
                        X.append(feats)
                        y.append(0)
                        loaded_custom = True
                    except Exception:
                        pass
        
        if os.path.exists(fake_dir):
            for f in os.listdir(fake_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    try:
                        img = Image.open(os.path.join(fake_dir, f)).convert("RGB")
                        feats = extract_forensics_features(img)
                        X.append(feats)
                        y.append(1)
                        loaded_custom = True
                    except Exception:
                        pass
                        
    # If no custom data was loaded, train on generated synthetic patterns
    if not loaded_custom:
        print("Generating synthetic dataset of forensics patterns...")
        for i in range(400):
            is_fake = (i % 2 == 1)
            img_bytes = generate_synthetic_image_bytes(is_fake)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            feats = extract_forensics_features(img)
            X.append(feats)
            y.append(1 if is_fake else 0)
            
    X = np.array(X)
    y = np.array(y)
    
    print(f"Dataset Size: {X.shape[0]} samples with {X.shape[1]} features.")
    
    # Train Random Forest Classifier
    rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=8)
    rf.fit(X, y)
    
    # Evaluate self-training accuracy
    preds = rf.predict(X)
    acc = np.mean(preds == y) * 100
    print(f"Random Forest Training Accuracy: {acc:.2f}%")
    
    # Save Random Forest Model
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "deepfake_rf.pkl")
    
    with open(model_path, "wb") as f:
        pickle.dump(rf, f)
        
    print(f"Model saved to {model_path}")
    return model_path
