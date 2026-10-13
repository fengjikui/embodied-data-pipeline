"""Align already calibrated numeric logs; preserve invalid samples explicitly."""
import argparse
import json
import math
from pathlib import Path
from vla_pipeline.io import digest, write_json
from vla_pipeline.synchronize import causal_align


def replace_nan(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, list):
        return [replace_nan(x) for x in value]
    if isinstance(value, dict):
        return {k: replace_nan(v) for k, v in value.items()}
    return value


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh alignment output')
    spec = json.loads(args.input.read_text(encoding='utf-8'))
    result = causal_align(spec['target_times'], spec['streams'], max_age_s=spec['max_age_s'], clock_id=spec['clock_id'])
    result['input_sha256'] = digest(args.input)
    write_json(args.output, replace_nan(result))
    print('Valid shared ticks:', sum(result['all_streams_valid']), '/', len(result['timestamps']))
