import os
import csv
import json
import random
from collections import defaultdict
import networkx as nx

def main():
    dataset_dir = r"C:\Users\DIVYA\Desktop\Desktopp\Datasets\FaceForensics++_C23"
    csv_dir = os.path.join(dataset_dir, 'csv')

    # 1. Collect all edges to form components
    manipulation_files = ['Deepfakes.csv', 'Face2Face.csv', 'FaceShifter.csv', 'FaceSwap.csv', 'NeuralTextures.csv']

    # Map edge to list of file paths & metadata
    components_graph = nx.Graph()
    video_records = []

    # Process original.csv
    with open(os.path.join(csv_dir, 'original.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = row['File Path']
            vid_id = os.path.basename(path).replace('.mp4', '')
            components_graph.add_node(vid_id)
            video_records.append({
                'path': path,
                'label': 'REAL',
                'manipulation': 'original',
                'nodes': [vid_id]
            })

    # Process manipulations
    for manip in manipulation_files:
        manip_name = manip.replace('.csv', '')
        with open(os.path.join(csv_dir, manip), 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = row['File Path']
                basename = os.path.basename(path).replace('.mp4', '')
                if '_' in basename:
                    a, b = basename.split('_')
                    components_graph.add_edge(a, b)
                    video_records.append({
                        'path': path,
                        'label': 'FAKE',
                        'manipulation': manip_name,
                        'nodes': [a, b]
                    })

    # Find components
    components = list(nx.connected_components(components_graph))
    print(f"Total components found: {len(components)}")
    assert len(components) == 500, "Expected exactly 500 components"

    # Sort components deterministically
    sorted_components = sorted([sorted(list(c)) for c in components])

    # Apply seed 42 and shuffle
    random.seed(42)
    shuffled_components = sorted_components.copy()
    random.shuffle(shuffled_components)

    # Split
    train_comps = shuffled_components[:350]
    val_comps = shuffled_components[350:425]
    test_comps = shuffled_components[425:]

    # Map node to split
    node_to_split = {}
    for c in train_comps:
        for node in c: node_to_split[node] = 'train'
    for c in val_comps:
        for node in c: node_to_split[node] = 'val'
    for c in test_comps:
        for node in c: node_to_split[node] = 'test'

    # Assign videos to splits
    split_manifest = []
    split_counts = {'train': {'REAL': 0, 'FAKE': 0}, 'val': {'REAL': 0, 'FAKE': 0}, 'test': {'REAL': 0, 'FAKE': 0}}
    manip_counts = defaultdict(lambda: defaultdict(int))
    seen_paths = set()

    for record in video_records:
        path = record['path']
        if path in seen_paths:
            raise ValueError(f"Duplicate video path found: {path}")
        seen_paths.add(path)

        # Determine split based on nodes
        assigned_splits = set(node_to_split[n] for n in record['nodes'] if n in node_to_split)
        if len(assigned_splits) != 1:
            raise ValueError(f"Video {record['path']} spans multiple splits or zero splits: {assigned_splits}")

        split = list(assigned_splits)[0]
        split_counts[split][record['label']] += 1
        manip_counts[split][record['manipulation']] += 1

        record['split'] = split
        split_manifest.append(record)

    # Validation checks
    assert split_counts['train']['REAL'] == 700 and split_counts['train']['FAKE'] == 3500
    assert split_counts['val']['REAL'] == 150 and split_counts['val']['FAKE'] == 750
    assert split_counts['test']['REAL'] == 150 and split_counts['test']['FAKE'] == 750

    # Save manifest CSV
    manifest_csv_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'deepfake_large_experiment_split_manifest.csv')
    with open(manifest_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'label', 'manipulation', 'split'])
        writer.writeheader()
        for rec in split_manifest:
            writer.writerow({k: rec[k] for k in ['path', 'label', 'manipulation', 'split']})

    # Save config JSON
    config_json_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'deepfake_large_experiment_config.json')
    config = {
        'seed': 42,
        'components_count': len(components),
        'split_component_counts': {'train': 350, 'val': 75, 'test': 75},
        'split_video_counts': split_counts,
        'manipulation_counts': manip_counts,
        'train_components': train_comps,
        'val_components': val_comps,
        'test_components': test_comps
    }
    with open(config_json_path, 'w') as f:
        json.dump(config, f, indent=4)

    print("Manifest and config saved securely.")
    print("Leakage verification passed: No videos span multiple splits. Components perfectly isolated.")
    print("Duplicate paths check passed.")
    print(f"Total videos split: {len(split_manifest)}")

if __name__ == '__main__':
    main()
