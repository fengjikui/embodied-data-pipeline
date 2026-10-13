"""Causal alignment for numeric streams. No physical clock calibration or drivers."""
from __future__ import annotations
import numpy as np


def causal_align(target_times, streams, *, max_age_s, clock_id):
    """Keep originals; select last sample <= target, mark stale/missing invalid.

    Inputs must ALREADY be in seconds on one calibrated clock. This function
    cannot infer offsets, drift, capture time versus receive time, or semantics.
    Numeric values only: image/MCAP/ROS2 adapters are not implemented here.
    """
    targets = np.asarray(target_times, dtype=np.float64)
    if targets.ndim != 1 or not len(targets) or not np.isfinite(targets).all() or np.any(np.diff(targets) <= 0):
        raise ValueError('Targets must be finite, strictly increasing seconds')
    if not isinstance(clock_id, str) or not clock_id.strip() or not streams:
        raise ValueError('Explicit clock and nonempty streams required')
    output = {}
    for name, stream in streams.items():
        if stream.get('clock_id') != clock_id or stream.get('time_unit') != 's':
            raise ValueError('Calibrate clocks and declare seconds before alignment')
        times = np.asarray(stream['timestamps'], dtype=np.float64)
        values = np.asarray(stream['values'], dtype=np.float64)
        limit = max_age_s.get(name)
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not np.isfinite(limit) or limit < 0:
            raise ValueError('Finite nonnegative per-stream age limit required')
        if times.ndim != 1 or not len(times) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
            raise ValueError('Stream times must be finite and strictly increasing')
        if values.ndim != 2 or len(values) != len(times) or not values.shape[1] or not np.isfinite(values).all():
            raise ValueError('Numeric values must be finite [time, channels]')
        indices = np.searchsorted(times, targets, side='right') - 1
        exists = indices >= 0
        safe = np.maximum(indices, 0)
        ages = targets - times[safe]
        valid = exists & (ages <= limit)
        selected = np.full((len(targets), values.shape[1]), np.nan)
        selected[valid] = values[safe[valid]]
        output[name] = {'values': selected.tolist(), 'valid': valid.tolist(),
                        'source_index': np.where(exists, indices, -1).tolist(),
                        'age_s': [float(ages[i]) if exists[i] else None for i in range(len(targets))]}
    return {'schema': 'causal_numeric_alignment_v1', 'clock_id': clock_id,
            'timestamps': targets.tolist(), 'streams': output,
            'all_streams_valid': np.logical_and.reduce([s['valid'] for s in output.values()]).tolist(),
            'physical_clock_calibration_verified': False}
