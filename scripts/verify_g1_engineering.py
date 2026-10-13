"""Reproduce the small XR-to-training chain and write dated, non-bulk evidence."""
import argparse
from datetime import date
import json
from pathlib import Path
import platform
import time
import numpy as np
import pyarrow.parquet as pq
from generate_g1_demo import generate
from resource_status import snapshot
from vla_pipeline.dataset import WindowDataset
from vla_pipeline.io import digest, write_json
from vla_pipeline.lerobot_export import export_plan, causal_native_images
from vla_pipeline.pipeline import run, verify_release
from vla_pipeline.register import register_local
from vla_pipeline.unitree import import_unitree


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workdir', type=Path, required=True, help='Fresh scratch directory')
    p.add_argument('--report-dir', type=Path, required=True)
    p.add_argument('--train-steps', type=int, default=0, help='Optional real CPU probe; requires Torch')
    p.add_argument('--checked-on', default=date.today().isoformat(), help='Evidence date, YYYY-MM-DD')
    args = p.parse_args(); started = time.perf_counter()
    if args.workdir.exists():
        raise FileExistsError('Use a fresh workdir; old versions are retained')
    resources = [{'phase': 'before', 'snapshot': snapshot()}]
    generate(args.workdir)
    receipt = import_unitree(args.workdir / 'capture', args.workdir / 'mapping.json', args.workdir / 'prepared')
    root = args.workdir / 'store'; lock = args.workdir / 'sources.lock.json'
    register_local(args.workdir / 'prepared', args.workdir / 'prepared/source.json', root, lock)
    recipe = json.loads(Path('configs/g1_edu_interface_recipe.json').read_text(encoding='utf-8'))
    manifest, _ = run(lock, root, True, recipe)
    release = root / 'releases' / manifest['release_id']
    assert manifest['accepted_episodes'] == 8 and manifest['numeric_frames'] == 192 and manifest['training_windows'] == 32
    assert len(receipt['original_files']) == 200
    for item in receipt['original_files']:
        original = args.workdir / 'capture' / item['path'].removeprefix('original/')
        assert digest(original) == item['sha256']
        assert digest(root / 'raw/g1_edu_synthetic/batch-001' / item['path']) == item['sha256']
    dataset = WindowDataset(release, 'g1_edu_synthetic')
    assert len(dataset) == 28
    val = WindowDataset(release, 'g1_edu_synthetic', 'validation'); assert len(val) == 4
    q = json.loads((release / 'quality.json').read_text(encoding='utf-8'))
    statistics = dataset.statistics
    assert set(statistics['fit_episode_ids']) == {r['episode_id'] for r in q['episodes'] if r['split'] == 'train'}
    max_error = 0.; padded = 0
    for file in (release / 'views/g1_edu_synthetic').rglob('*.npz'):
        rows = pq.read_table(release / 'canonical/g1_edu_synthetic' / (file.stem + '.parquet')).to_pylist()
        raw_actions = np.asarray([r['action'] for r in rows])
        with np.load(file, allow_pickle=False) as arrays:
            for idx, anchor in enumerate(arrays['anchor_index']):
                valid = min(8, len(rows) - anchor)
                assert arrays['action_mask'][idx, :valid].all() and not arrays['action_mask'][idx, valid:].any()
                restored = dataset.denormalize_action(arrays['actions'][idx, :valid])
                max_error = max(max_error, float(np.max(np.abs(restored - raw_actions[anchor:anchor + valid]))))
            padded += int((~arrays['action_mask']).sum())
    assert max_error < 1e-5
    again, cached = run(lock, root, True, recipe); assert cached and again == manifest
    alternate, _ = run(lock, root, True, dict(recipe, horizon=4, anchor_stride=4))
    assert alternate['release_id'] != manifest['release_id']; verify_release(release)
    _, native = export_plan(release, root / 'raw', 'g1_edu_synthetic', 'train')
    native_frames = sum(sum(1 for _ in causal_native_images(ep)) for ep in native)
    assert native_frames == 168
    first = dataset[0]
    batch = {'release_id': manifest['release_id'], 'train_samples': len(dataset), 'validation_samples': len(val),
             'fields': {k: {'shape': list(v.shape), 'dtype': str(v.dtype)} if isinstance(v, np.ndarray) else v for k, v in first.items()}}
    probe = None
    if args.train_steps:
        resources.append({'phase': 'before_cpu_probe', 'snapshot': snapshot()})
        from vla_pipeline.training import train_probe
        probe = train_probe(release, args.workdir / 'training', steps=args.train_steps, threads=1)
        write_json(args.report_dir / 'synthetic_training_probe.json', probe)
    resources.append({'phase': 'after', 'snapshot': snapshot()})
    date.fromisoformat(args.checked_on)
    result = {'checked_on': args.checked_on, 'purpose': 'Synthetic engineering reproduction; NOT collected G1 data, physics simulation or robot capability evaluation',
              'release_id': manifest['release_id'], 'alternate_release_id': alternate['release_id'], 'pipeline_code_sha256': manifest['code_sha256'],
              'python': platform.python_version(), 'platform': platform.platform(), 'counts': {'episodes': 8, 'numeric_frames': 192, 'windows': 32, 'train_windows': 28, 'validation_windows': 4, 'original_files_preserved': 200, 'full_frame_export_preflight_train_frames': native_frames},
              'checks': {'original_file_bytes_preserved': True, 'train_only_statistics': True, 'bounded_action_windows': True, 'masked_padding_elements': padded, 'action_roundtrip_max_abs_error': max_error, 'same_recipe_idempotent': True, 'new_recipe_new_release': True, 'old_release_integrity_verified': True, 'full_frame_causal_replay': True},
              'official_lerobot_sdk_export': 'not_executed_by_this_script; separate SDK receipt required', 'deployment_ready': False, 'wall_seconds': round(time.perf_counter() - started, 3)}
    write_json(args.report_dir / 'synthetic_acceptance.json', result)
    write_json(args.report_dir / 'synthetic_batch.json', batch)
    write_json(args.report_dir / 'synthetic_manifest.json', manifest)
    write_json(args.report_dir / 'resource_snapshots.json', resources)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
