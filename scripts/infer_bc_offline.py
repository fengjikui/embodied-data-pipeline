"""Read one held-out window and restore a toy checkpoint; never send actions."""
import argparse
import json
from pathlib import Path
import torch
from vla_pipeline.dataset import WindowDataset
from vla_pipeline.io import digest, write_json
from vla_pipeline.training import TinyMultimodalBC, tokenize

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release', type=Path, required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError('Use a fresh inference output')
    torch.set_num_threads(1)
    dataset = WindowDataset(a.release, a.source, 'validation')
    payload = torch.load(a.checkpoint, weights_only=True, map_location='cpu')
    if payload['release_id'] != dataset.release_id or payload['statistics_sha256'] != digest(a.release / 'statistics.json'):
        raise ValueError('Checkpoint data/statistics mismatch')
    row = dataset[0]
    model = TinyMultimodalBC(**payload['dims']); model.load_state_dict(payload['model']); model.eval()
    with torch.no_grad():
        prediction = model(torch.from_numpy(row['image']).unsqueeze(0), torch.from_numpy(row['state']).unsqueeze(0), tokenize([row['language']]))[0].numpy()
    result = {'purpose': 'Offline toy BC inference; synthetic channels; no driver or robot command',
              'release_id': dataset.release_id, 'checkpoint_sha256': digest(a.checkpoint),
              'language': row['language'], 'timestamp': row['timestamp'],
              'normalized_prediction': prediction.tolist(), 'native_prediction': dataset.denormalize_action(prediction).tolist(),
              'native_label': dataset.denormalize_action(row['actions']).tolist(), 'action_mask': row['action_mask'].tolist(),
              'robot_command_sent': False}
    write_json(a.output, result)
    print('Offline predicted chunk:', list(prediction.shape), 'robot_command_sent=False')
