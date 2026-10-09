import os
import sys
import csv
import json
import time
import cv2
from PIL import Image
import concurrent.futures
from threading import Lock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.face_extractor import OpenCVDNNFaceExtractor

def safe_atomic_write(temp_path, final_path, write_func):
    try:
        write_func(temp_path)
        os.replace(temp_path, final_path)
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

log_lock = Lock()

def process_video(row, dataset_dir, cache_dir, fractions, target_size=(224, 224)):
    vpath = os.path.join(dataset_dir, row['path'].replace('/', '\\'))
    vid_id = os.path.basename(row['path']).replace('.mp4', '')

    vid_cache_dir = os.path.join(cache_dir, row['manipulation'], vid_id)
    os.makedirs(vid_cache_dir, exist_ok=True)

    meta_final = os.path.join(vid_cache_dir, "metadata.json")
    if os.path.exists(meta_final):
        try:
            with open(meta_final, 'r') as f:
                existing_meta = json.load(f)
            if existing_meta.get('extracted_count', 0) == len(fractions):
                return {'success': True, 'cached': True, 'vid_id': vid_id, 'bytes': 0, 'meta': existing_meta}
        except:
            pass # Invalid meta, recompute

    vid_meta = {
        'source_path': row['path'],
        'label': row['label'],
        'split': row['split'],
        'manipulation': row['manipulation'],
        'fractions': fractions,
        'target_size': target_size,
        'prep_version': '1.0',
        'extracted_count': 0,
        'frames': []
    }

    extractor = OpenCVDNNFaceExtractor(target_size=target_size)
    success_count = 0
    total_bytes = 0

    try:
        cap = cv2.VideoCapture(vpath)
        if cap.isOpened():
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames > 0:
                for frac in fractions:
                    target_idx = int(frac * (total_frames - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
                    ret, frame = cap.read()

                    if ret and frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        try:
                            faces = extractor.extract_faces(frame_rgb, max_faces=1)
                            if faces:
                                img_np = faces[0]
                                method = 'dnn_extracted'
                            else:
                                img_np = cv2.resize(frame_rgb, target_size)
                                method = 'full_frame_fallback'
                        except:
                            img_np = cv2.resize(frame_rgb, target_size)
                            method = 'full_frame_fallback'

                        img = Image.fromarray(img_np)
                        fname = f"frame_{int(frac*100)}_{method}.jpg"
                        final_p = os.path.join(vid_cache_dir, fname)
                        temp_p = final_p + ".tmp"

                        def do_save(p):
                            img.save(p, format='JPEG', quality=95)

                        try:
                            safe_atomic_write(temp_p, final_p, do_save)
                            size_bytes = os.path.getsize(final_p)
                            total_bytes += size_bytes
                            success_count += 1

                            vid_meta['frames'].append({
                                'fraction': frac, 'file': fname, 'status': 'success',
                                'method': method, 'bytes': size_bytes
                            })
                        except Exception as e:
                            vid_meta['frames'].append({'fraction': frac, 'status': f'failed_save:{e}'})
                    else:
                        vid_meta['frames'].append({'fraction': frac, 'status': 'failed_read'})
        cap.release()
    except Exception as e:
        vid_meta['error'] = str(e)

    vid_meta['extracted_count'] = success_count
    def save_meta(p):
        with open(p, 'w') as mf:
            json.dump(vid_meta, mf, indent=4)
    safe_atomic_write(meta_final + '.tmp', meta_final, save_meta)

    return {'success': success_count == len(fractions), 'cached': False, 'vid_id': vid_id, 'bytes': total_bytes, 'meta': vid_meta, 'count': success_count}

def run_preparation():
    print("="*60)
    print("DEEPFAKE FACE CACHE - FULL PREPARATION")
    print("="*60)

    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(project_dir, 'models', 'deepfake_large_experiment_split_manifest.csv')
    cache_dir = os.path.join(project_dir, 'data', 'deepfake_face_cache')
    os.makedirs(cache_dir, exist_ok=True)

    dataset_dir = r"C:\Users\DIVYA\Desktop\Desktopp\Datasets\FaceForensics++_C23"

    all_videos = []
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_videos.append(row)

    print(f"Loaded {len(all_videos)} total videos to process.")

    fractions = [0.1, 0.3, 0.5, 0.7, 0.9]
    t0 = time.time()

    # Track stats
    total_bytes = 0
    extracted = 0
    requested = len(all_videos) * len(fractions)

    counts = {'zero': 0, 'partial': 0, 'complete': 0}
    cached_skips = 0

    # We will use ThreadPoolExecutor which works fine for this CV2 IO workload
    processed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_video, row, dataset_dir, cache_dir, fractions): row for row in all_videos}

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            processed += 1
            if processed % 100 == 0:
                print(f"Processed {processed}/{len(all_videos)} videos... (Elapsed: {time.time()-t0:.1f}s)")

            if res['cached']:
                cached_skips += 1
                c = res['meta'].get('extracted_count', 0)
                extracted += c
                if c == len(fractions): counts['complete'] += 1
                elif c == 0: counts['zero'] += 1
                else: counts['partial'] += 1
            else:
                total_bytes += res['bytes']
                c = res['count']
                extracted += c
                if c == len(fractions): counts['complete'] += 1
                elif c == 0: counts['zero'] += 1
                else: counts['partial'] += 1

    elapsed = time.time() - t0

    print(f"\nProcessing Complete in {elapsed:.2f}s!")
    print(f"Skipped {cached_skips} already cached videos.")
    print(f"Total Bytes Written (New): {total_bytes/1024/1024:.2f} MB")

    report = {
        'total_videos_processed': len(all_videos),
        'decoding_time_seconds': elapsed,
        'requested_frames': requested,
        'successfully_extracted_frames': extracted,
        'videos_complete_success': counts['complete'],
        'videos_partial_success': counts['partial'],
        'videos_zero_success': counts['zero'],
        'already_cached_videos': cached_skips,
        'new_bytes_written_mb': total_bytes / 1024 / 1024
    }

    report_path = os.path.join(project_dir, 'logs', 'deepfake_face_cache_full_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=4)

    print(f"Full report saved to {report_path}")

if __name__ == '__main__':
    run_preparation()
