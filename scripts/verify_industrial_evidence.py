"""Check dated teaching evidence consistency; optionally inspect local artifacts."""
import argparse
import json
from pathlib import Path
import numpy as np
from vla_pipeline.io import digest, write_json
from vla_pipeline.pipeline import code_hash, verify_release


def verify(report, check_local=False):
    def read(name):
        return json.loads((report/name).read_text(encoding='utf-8'))
    acceptance=read('synthetic_acceptance.json'); bc=read('synthetic_training_probe.json'); prediction=read('offline_prediction.json')
    assert acceptance['release_id']==bc['release_id']==prediction['release_id']
    assert acceptance['pipeline_code_sha256']==code_hash()
    assert acceptance['deployment_ready'] is False and prediction['robot_command_sent'] is False
    assert acceptance['counts']['episodes']==8 and acceptance['counts']['windows']==32
    assert bc['results'][0]['finite_gradients'] and bc['results'][0]['checkpoint_reload_max_abs_error']==0
    assert np.asarray(prediction['native_prediction']).shape==(8,2)
    act=read('act-training.json'); infer=read('act-inference.json')
    assert act['steps']==5 and [r['step'] for r in act['losses']]==list(range(1,6))
    assert act['checkpoint_files_sha256']['model.safetensors']==infer['checkpoint_sha256']
    assert act['sdk_commit']==infer['sdk_commit'] and infer['saved_training_processors_used']
    assert infer['action_shape']==[2,8,2] and infer['label_passed_as_input'] is False
    assert act['robot_command_sent'] is False and infer['robot_command_sent'] is False
    sdk=read('sdk/g1_edu_synthetic-sdk-summary.json')
    assert sum(r['frames'] for r in sdk['results'])==192
    for receipt in sdk['results']:
        assert receipt['all_frame_action_labels_checked'] and receipt['canonical_label_roundtrip_max_abs_error']<1e-5
        assert all(row['last_frame_pad_mask']==[False]+[True]*7 for row in receipt['official_episode_boundary_padding_checked'])
    aligned=read('aligned.json'); audit=read('intake_audit.json')
    assert aligned['all_streams_valid']==[False,True,True,False,True]
    assert aligned['streams']['wrist_force']['source_index'][0]==-1
    assert audit['document_checks_passed'] is False and audit['robot_deployment_authorized'] is False
    ppo=read('ppo_report.json'); play=read('actor_play.json')
    assert ppo['checkpoint_sha256']==play['checkpoint_sha256']
    assert ppo['script_sha256']==digest(Path('scripts/ppo_position_lab.py'))
    assert ppo['rollout_shapes']['observation']==[48,16,4]
    assert ppo['robot_command_sent'] is False and play['robot_command_sent'] is False
    assert ppo['final_evaluation']==play['evaluation']
    html=read('offline-report-build.json')
    assert html['html_sha256']==digest(Path('deliverables/industrial-report.html'))
    for name, sha in html['markdown_sha256'].items():
        assert digest(Path(name))==sha
    browser=read('browser-qa.json')
    assert browser['html_sha256']==digest(Path('deliverables/industrial-report.html'))
    assert browser['qa_script_sha256']==digest(Path('scripts/verify_industrial_report.mjs'))
    assert all(browser['checks'].values()) and not browser['errors'] and not browser['remoteRequests']
    tests=read('tests.json')
    assert tests['failures']==tests['errors']==tests['skipped']==0 and tests['tests']>=52
    local_checks=[]
    if check_local:
        root=Path('data/industrial-lab-accepted-2026-10-14')
        release=root/'store/releases'/acceptance['release_id']; verify_release(release)
        assert digest(root/'training/g1_edu_synthetic.pt')==prediction['checkpoint_sha256']
        assert digest(Path('data/ppo-lab-2026-10-14/ppo_actor_critic.pt'))==ppo['checkpoint_sha256']
        checkpoint=Path('data/industrial-act-accepted-2026-10-14/checkpoints/000005/pretrained_model')
        for name,sha in act['checkpoint_files_sha256'].items(): assert digest(checkpoint/name)==sha
        for split in ('train','validation'):
            receipt=read('sdk/g1_edu_synthetic-'+split+'-sdk.json')
            for name,sha in receipt['export_output_sha256'].items():
                assert digest(Path('data/industrial-sdk-2026-10-14')/split/name)==sha
        local_checks=['immutable_release','BC_checkpoint','PPO_checkpoint','ACT_checkpoint_bundle','all_SDK_export_files']
    result={'checked_on':'2026-10-14','schema':'industrial_teaching_evidence_audit_v1',
            'report_consistency_passed':True,'local_artifacts_checked':local_checks,
            'robot_capability_verified':False,'production_pipeline_deployed':False,
            'scope':'Only dated synthetic teaching and document evidence; does not certify robot or production capability.'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report-dir',type=Path,default=Path('reports/industrial-2026-10-14'))
    p.add_argument('--check-local-artifacts',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args(); result=verify(a.report_dir,a.check_local_artifacts)
    if a.output: write_json(a.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
