"""Fail-closed document preflight, NOT certification or a robot safety system."""
from pathlib import Path
import math
from .io import confined, digest

REQUIRED_EVIDENCE = ('hardware', 'calibration', 'clock_validation', 'controller', 'data_rights', 'task_acceptance')


def audit_contract(spec, evidence_root):
    errors = []
    if spec.get('schema') != 'industrial_intake_v1':
        errors.append('schema must be industrial_intake_v1')
    for key in ('robot_id', 'robot_configuration', 'task_id', 'session_id', 'clock_id', 'controller_id'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            errors.append(key + ' missing')
    if spec.get('timestamp_basis') != 'measured_capture_time':
        errors.append('measured capture time and clock validation required')
    for key in ('state_channels', 'action_channels'):
        channels = spec.get(key)
        if not isinstance(channels, list) or not channels:
            errors.append(key + ' missing'); continue
        names = []
        for channel in channels:
            if not isinstance(channel, dict):
                errors.append(key + ' invalid channel'); continue
            names.append(channel.get('name'))
            if any(not isinstance(channel.get(k), str) or not channel[k].strip() for k in ('name', 'unit', 'frame', 'meaning')):
                errors.append(key + ' missing channel semantics')
            bounds = channel.get('range')
            if not isinstance(bounds, list) or len(bounds) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in bounds) or bounds[0] >= bounds[1]:
                errors.append(key + ' invalid finite range')
        if len({n for n in names if isinstance(n, str)}) != len(names):
            errors.append(key + ' names missing or duplicate')
    evidence = spec.get('evidence', {})
    if not isinstance(evidence, dict):
        evidence = {}
    verified = {}
    for key in REQUIRED_EVIDENCE:
        item = evidence.get(key)
        if not isinstance(item, dict) or not isinstance(item.get('path'), str) or not isinstance(item.get('sha256'), str):
            errors.append('evidence missing: ' + key); continue
        try:
            path = confined(Path(evidence_root), item['path'])
            if not path.is_file() or digest(path) != item['sha256']:
                raise ValueError('missing or digest mismatch')
            verified[key] = item['sha256']
        except (OSError, ValueError) as exc:
            errors.append('evidence invalid: ' + key + ': ' + str(exc))
    return {'schema': 'industrial_intake_audit_v1', 'document_checks_passed': not errors,
            'blockers': errors, 'evidence_hashes_verified': verified,
            'human_review_required': True, 'robot_deployment_authorized': False,
            'scope': 'Checks declared fields and file hashes only; cannot verify physical calibration, data rights, controller safety or industrial capability.'}
