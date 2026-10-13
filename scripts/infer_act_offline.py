"""Official pinned ACT checkpoint inference on held-out frames, no robot I/O."""
import argparse
import importlib.metadata
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from vla_pipeline.io import digest, write_json
from vla_pipeline.lerobot_export import SDK_COMMIT, sdk_commit


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--dataset-root',type=Path,required=True)
    p.add_argument('--repo-id',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError('Use fresh output file')
    torch.set_num_threads(1)
    import lerobot.datasets.lerobot_dataset as sdk
    if sdk_commit(sdk)!=SDK_COMMIT: raise ValueError('Wrong SDK commit')
    from lerobot.policies.act.modeling_act import ACTPolicy
    from lerobot.policies import make_pre_post_processors
    ds=sdk.LeRobotDataset(repo_id=a.repo_id,root=a.dataset_root,video_backend='pyav')
    batch=next(iter(DataLoader(ds,batch_size=2,num_workers=0,shuffle=False)))
    policy=ACTPolicy.from_pretrained(str(a.checkpoint));policy.eval()
    pre,post=make_pre_post_processors(policy.config,pretrained_path=str(a.checkpoint),
                                     preprocessor_overrides={'device_processor':{'device':'cpu'}})
    # Only deploy-time observations. No target action, future outcome or task label.
    inputs={k:v for k,v in batch.items() if k in policy.config.input_features}
    with torch.no_grad():
        processed=pre(inputs)
        normalized=policy.predict_action_chunk(processed)
        native=post(normalized)
    if not bool(torch.isfinite(native).all()): raise ValueError('Nonfinite ACT output')
    write_json(a.output,{'purpose':__doc__,'sdk_commit':SDK_COMMIT,'sdk_version':importlib.metadata.version('lerobot'),
                         'checkpoint_sha256':digest(a.checkpoint/'model.safetensors'),
                         'input_shapes':{k:list(v.shape) for k,v in inputs.items()},
                         'action_shape':list(native.shape),'native_prediction':native.tolist(),
                         'saved_training_processors_used':True,'label_passed_as_input':False,
                         'dataset_role':'held_out_validation','robot_command_sent':False})
    print('Official ACT native chunk:',list(native.shape),'no label input or robot command')
