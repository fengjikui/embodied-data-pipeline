"""Run five official ACT updates, pinned SDK, synthetic export, CPU, no downloads."""
import argparse
from datetime import date
import importlib.metadata
import os
from pathlib import Path
import re
import subprocess
import sys
from resource_status import snapshot
from vla_pipeline.io import digest, write_json
from vla_pipeline.lerobot_export import SDK_COMMIT, sdk_commit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset-root',type=Path,required=True);p.add_argument('--repo-id',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--checked-on',default=date.today().isoformat())
    a=p.parse_args()
    date.fromisoformat(a.checked_on)
    if a.output.exists() or a.report.exists(): raise FileExistsError('Use fresh output and report')
    import lerobot.datasets.lerobot_dataset as sdk
    if sdk_commit(sdk)!=SDK_COMMIT: raise ValueError('Wrong official SDK commit')
    cmd=[sys.executable,'-m','lerobot.scripts.lerobot_train',f'--dataset.repo_id={a.repo_id}',
         f'--dataset.root={a.dataset_root.resolve()}','--dataset.video_backend=pyav','--policy.type=act',
         '--policy.device=cpu','--policy.push_to_hub=false','--policy.pretrained_backbone_weights=null',
         '--policy.chunk_size=8','--policy.n_action_steps=8','--policy.dim_model=64','--policy.n_heads=4',
         '--policy.dim_feedforward=128','--policy.n_encoder_layers=1','--policy.n_decoder_layers=1',
         '--policy.n_vae_encoder_layers=1','--policy.latent_dim=8','--batch_size=2','--num_workers=0',
         '--steps=5','--save_freq=5','--log_freq=1','--env_eval_freq=0','--eval_steps=0',
         '--wandb.enable=false',f'--output_dir={a.output.resolve()}']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    resources=[{'phase':'before','snapshot':snapshot()}]
    log=a.output.parent/(a.output.name+'-trainer.log')
    log.parent.mkdir(parents=True,exist_ok=True)
    if log.exists(): raise FileExistsError('Use fresh trainer log')
    with log.open('w',encoding='utf-8') as handle:
        completed=subprocess.run(cmd,env=env,stdout=handle,stderr=subprocess.STDOUT)
    resources.append({'phase':'after','snapshot':snapshot()})
    if completed.returncode: raise RuntimeError(f'Official trainer failed; inspect {log}')
    text=log.read_text(encoding='utf-8')
    matches=re.findall(r'step:(\d+).*?loss:([\d.]+).*?l1_loss:([\d.]+).*?kld_loss:([\d.]+)',text)
    if len(matches)!=5: raise ValueError('Five update log records required')
    checkpoint=a.output/'checkpoints/000005/pretrained_model'
    required=('model.safetensors','config.json','train_config.json','policy_preprocessor.json','policy_postprocessor.json')
    hashes={name:digest(checkpoint/name) for name in required}
    import json
    metadata=json.loads((a.dataset_root/'meta/info.json').read_text(encoding='utf-8'))
    write_json(a.report,{'checked_on':a.checked_on,'purpose':__doc__,'sdk_commit':SDK_COMMIT,
                         'sdk_version':importlib.metadata.version('lerobot'),'accelerate_version':importlib.metadata.version('accelerate'),
                         'dataset_info_sha256':digest(a.dataset_root/'meta/info.json'),
                         'dataset_frames':metadata['total_frames'],'dataset_episodes':metadata['total_episodes'],
                         'device':'cpu','threads_env':1,'steps':5,'commands':cmd[1:],
                         'losses':[{'step':int(s),'total':float(t),'l1':float(l),'kl':float(k)} for s,t,l,k in matches],
                         'checkpoint_files_sha256':hashes,'trainer_log_sha256':digest(log),
                         'pretrained_weights_downloaded':False,'robot_command_sent':False,'resource_snapshots':resources})
    print('Five official ACT updates accepted, checkpoint saved:',checkpoint)
