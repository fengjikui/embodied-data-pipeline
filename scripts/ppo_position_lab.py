"""CPU PPO lesson in a fictional 1D environment, NOT G1 or physics simulation."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.distributions import Normal
from resource_status import snapshot
from vla_pipeline.io import write_json, digest

STEPS = 48


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        self.actor = nn.Sequential(nn.Linear(4, 32), nn.Tanh(), nn.Linear(32, 1))
        self.critic = nn.Sequential(nn.Linear(4, 32), nn.Tanh(), nn.Linear(32, 1))
        self.log_std = nn.Parameter(torch.tensor([-0.5]))

    def distribution(self, obs):
        return Normal(self.actor(obs).squeeze(-1), self.log_std.exp())


def observation(x, v, goal, tick):
    return torch.stack((x, v, goal, torch.full_like(x, 1 - tick / STEPS)), dim=-1)


def transition(x, v, raw_action, goal):
    action = torch.tanh(raw_action)  # bounded action; store raw latent for PPO likelihood
    new_v = .85 * v + .15 * action
    new_x = x + .1 * new_v
    reward = -(new_x - goal).square() - .01 * action.square()
    return new_x, new_v, reward, action


@torch.no_grad()
def evaluate(model):
    x = torch.linspace(-1, 1, 32); v = torch.zeros_like(x); goal = torch.zeros_like(x)
    returns = torch.zeros_like(x); trajectory = []
    for tick in range(STEPS):
        obs = observation(x, v, goal, tick)
        raw = model.actor(obs).squeeze(-1)
        x, v, reward, action = transition(x, v, raw, goal)
        returns += reward
        trajectory.append({'step': tick, 'example_x': float(x[0]), 'example_v': float(v[0]), 'action': float(action[0]), 'reward': float(reward[0])})
    return {'mean_return': float(returns.mean()), 'mean_final_absolute_error': float((x-goal).abs().mean()),
            'evaluation_initial_conditions': '32 fixed positions evenly spaced in [-1,1], zero target and velocity', 'example_trajectory': trajectory}


def train(output, updates):
    if output.exists():
        raise FileExistsError('Use fresh output directory')
    if updates < 1:
        raise ValueError('updates must be positive')
    output.mkdir(parents=True); resources = [{'phase': 'before', 'snapshot': snapshot()}]
    torch.set_num_threads(1); torch.manual_seed(7)
    model = ActorCritic(); optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    initial = evaluate(model); history = []; saved_rollout = None
    for update in range(updates):
        x = torch.rand(16) * 2 - 1; v = torch.zeros_like(x); goal = torch.zeros_like(x)
        observations=[]; raws=[]; rewards=[]; old_log_probs=[]; values=[]; actions=[]
        for tick in range(STEPS):
            obs = observation(x, v, goal, tick)
            with torch.no_grad():
                dist = model.distribution(obs); raw = dist.sample(); value = model.critic(obs).squeeze(-1)
                logprob = dist.log_prob(raw)
                x, v, reward, action = transition(x, v, raw, goal)
            observations.append(obs); raws.append(raw); rewards.append(reward)
            old_log_probs.append(logprob); values.append(value); actions.append(action)
        obs = torch.stack(observations); raw = torch.stack(raws); reward = torch.stack(rewards)
        old_lp = torch.stack(old_log_probs); old_v = torch.stack(values)
        advantages = torch.zeros_like(reward); gae = torch.zeros(16)
        # Fixed 48-step finite-horizon MDP: final transition is terminal, not a truncation.
        # Remaining time is in observation, and terminal bootstrap is exactly zero.
        for tick in reversed(range(STEPS)):
            next_v = old_v[tick+1] if tick+1 < STEPS else torch.zeros(16)
            live = 1. if tick+1 < STEPS else 0.
            delta = reward[tick] + .98 * next_v * live - old_v[tick]
            gae = delta + .98 * .95 * live * gae
            advantages[tick] = gae
        returns = advantages + old_v
        if saved_rollout is None:
            done = np.zeros((STEPS,16), dtype=bool); done[-1] = True
            saved_rollout = dict(observation=obs.numpy(), raw_action=raw.numpy(), action=torch.stack(actions).numpy(),
                                 reward=reward.numpy(), done=done, old_log_prob=old_lp.numpy(), value=old_v.numpy(),
                                 advantage=advantages.numpy(), returns=returns.numpy())
            np.savez_compressed(output / 'first_rollout.npz', **saved_rollout)
        flat_obs = obs.reshape(-1,4); flat_raw=raw.flatten(); flat_lp=old_lp.flatten(); flat_ret=returns.flatten()
        flat_adv=advantages.flatten(); flat_adv=(flat_adv-flat_adv.mean())/(flat_adv.std()+1e-8)
        for epoch in range(4):
            for ids in torch.randperm(len(flat_raw)).split(128):
                dist = model.distribution(flat_obs[ids]); new_lp=dist.log_prob(flat_raw[ids])
                ratio=(new_lp-flat_lp[ids]).exp()
                actor_loss=-torch.minimum(ratio*flat_adv[ids], ratio.clamp(.8,1.2)*flat_adv[ids]).mean()
                critic_loss=(model.critic(flat_obs[ids]).squeeze(-1)-flat_ret[ids]).square().mean()
                # Entropy regularizes the LATENT Gaussian; tanh-Jacobian cancels in PPO ratio.
                loss=actor_loss + .5*critic_loss - .001*dist.entropy().mean()
                if not bool(torch.isfinite(loss)): raise ValueError('Nonfinite PPO loss')
                optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.); optimizer.step()
        if update % 10 == 0 or update == updates-1:
            metrics={'update': update+1, 'rollout_mean_return': float(reward.sum(0).mean()),
                     'actor_loss': float(actor_loss.detach()), 'critic_loss': float(critic_loss.detach())}
            history.append(metrics); print(metrics,flush=True)
            resources.append({'phase': 'update-'+str(update+1), 'snapshot': snapshot()})
    final = evaluate(model)
    checkpoint=output/'ppo_actor_critic.pt'
    torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'seed':7, 'updates':updates,
                'environment':'fictional_1d_position_v1','script_sha256':digest(Path(__file__))},checkpoint)
    result={'purpose':'PPO actor/critic/GAE/likelihood/inference teaching ONLY; not locomotion, contact simulation or G1 deployment',
            'device':'cpu','threads':1,'seed':7,'updates':updates,'gamma':.98,'gae_lambda':.95,'clip':.2,
            'initial_evaluation':initial,'final_evaluation':final,'curve':history,
            'rollout_shapes':{k:list(v.shape) for k,v in saved_rollout.items()},
            'checkpoint_sha256':digest(checkpoint),'script_sha256':digest(Path(__file__)),
            'robot_command_sent':False,'resource_snapshots':resources}
    write_json(output/'ppo_report.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    tr=sub.add_parser('train'); tr.add_argument('--output',type=Path,required=True); tr.add_argument('--updates',type=int,default=60)
    pl=sub.add_parser('play'); pl.add_argument('--checkpoint',type=Path,required=True); pl.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='train': train(a.output,a.updates)
    else:
        if a.output.exists(): raise FileExistsError('Use fresh output file')
        torch.set_num_threads(1)
        data=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
        if data['environment']!='fictional_1d_position_v1' or data['script_sha256']!=digest(Path(__file__)):
            raise ValueError('Checkpoint environment or source version mismatch')
        model=ActorCritic();model.load_state_dict(data['model']);model.eval()
        write_json(a.output,{'purpose':__doc__, 'actor_only_action_generation':True,'robot_command_sent':False,
                             'evaluation':evaluate(model),'checkpoint_sha256':digest(a.checkpoint)})
        print('Actor inference completed in fictional environment, no robot commands')
