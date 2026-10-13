import copy
import json
from pathlib import Path
import numpy as np
import pytest
from vla_pipeline.synchronize import causal_align
from vla_pipeline.industrial_contract import audit_contract, REQUIRED_EVIDENCE
from vla_pipeline.io import digest


def alignment_spec():
    return json.loads(Path('configs/async_numeric_demo.json').read_text())


def test_no_future_frame_and_stale_sample_is_invalid():
    d = alignment_spec()
    r = causal_align(d['target_times'], d['streams'], max_age_s=d['max_age_s'], clock_id=d['clock_id'])
    assert r['streams']['wrist_force']['source_index'] == [-1, 0, 1, 2, 3]
    assert r['streams']['joint_state']['valid'] == [True, True, True, False, True]
    assert r['all_streams_valid'] == [False, True, True, False, True]
    assert np.isnan(r['streams']['joint_state']['values'][3]).all()


@pytest.mark.parametrize('corruption', ['clock', 'unit', 'duplicate_time', 'nan', 'negative_age'])
def test_alignment_rejects_ambiguous_timing(corruption):
    d = alignment_spec(); s = d['streams']['joint_state']
    if corruption == 'clock': s['clock_id'] = 'another_device'
    if corruption == 'unit': s['time_unit'] = 'ms'
    if corruption == 'duplicate_time': s['timestamps'][1] = 0
    if corruption == 'nan': s['values'][0][0] = float('nan')
    if corruption == 'negative_age': d['max_age_s']['joint_state'] = -1
    with pytest.raises(ValueError):
        causal_align(d['target_times'], d['streams'], max_age_s=d['max_age_s'], clock_id=d['clock_id'])


def valid_contract(tmp_path):
    # These are dummy DOCUMENTS for unit testing, not physical attestations.
    channels = [{'name': 'fictional', 'unit': 'unit', 'frame': 'fictional', 'meaning': 'test only', 'range': [-1, 1]}]
    d = {'schema': 'industrial_intake_v1', 'robot_id': 'test', 'robot_configuration': 'test', 'task_id': 'test',
         'session_id': 'test', 'clock_id': 'test', 'controller_id': 'test', 'timestamp_basis': 'measured_capture_time',
         'state_channels': channels, 'action_channels': copy.deepcopy(channels), 'evidence': {}}
    for key in REQUIRED_EVIDENCE:
        p = tmp_path / (key + '.txt'); p.write_text('DUMMY DOCUMENT: ' + key)
        d['evidence'][key] = {'path': p.name, 'sha256': digest(p)}
    return d


def test_template_blocks_and_documents_cannot_authorize_robot(tmp_path):
    d = json.loads(Path('configs/industrial_intake.template.json').read_text())
    assert not audit_contract(d, tmp_path)['document_checks_passed']
    result = audit_contract(valid_contract(tmp_path), tmp_path)
    assert result['document_checks_passed'] and result['human_review_required']
    assert result['robot_deployment_authorized'] is False


@pytest.mark.parametrize('corruption', ['hash', 'traversal', 'nominal_time', 'duplicate_channel', 'nonfinite_range'])
def test_contract_rejects_forged_or_incomplete_evidence(tmp_path, corruption):
    d = valid_contract(tmp_path)
    if corruption == 'hash': d['evidence']['hardware']['sha256'] = '0' * 64
    if corruption == 'traversal': d['evidence']['hardware']['path'] = '../outside.txt'
    if corruption == 'nominal_time': d['timestamp_basis'] = 'nominal_index'
    if corruption == 'duplicate_channel': d['action_channels'].append(copy.deepcopy(d['action_channels'][0]))
    if corruption == 'nonfinite_range': d['action_channels'][0]['range'][1] = float('inf')
    assert not audit_contract(d, tmp_path)['document_checks_passed']
