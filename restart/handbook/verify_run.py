"""Audit a completed local handbook run; emits a small, non-data evidence report."""
import argparse
import json
from pathlib import Path
import re

import lab


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--training-name", default="act")
    p.add_argument("--prediction", default="prediction-verified.json")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.root
    plan = lab.read(lab.HERE / "sources.lock.json")
    download = lab.read(root / "real/download_receipt.json")
    assert download["revision"] == plan["real_dataset"]["revision"]
    for item in plan["real_dataset"]["files"]:
        path = root / "real" / item["path"]
        assert path.stat().st_size == item["bytes"] and lab.digest(path) == item["sha256"]
    real = lab.inspect_real(root / "real")
    exported = lab.read(root / "dataset/export_receipt.json")
    assert exported["roles"]["train"]["episodes"] == [0, 1, 2]
    assert exported["roles"]["validation"]["episodes"] == [3]
    assert exported["roles"]["train"]["frames"] == 60
    assert exported["roles"]["validation"]["frames"] == 20
    lab.verify(root / "capture", root / "dataset/source_snapshot.json")
    report = lab.read(root / args.training_name / "lab_receipt.json")
    assert report["lab_code_sha256"] == lab.digest(lab.__file__)
    lab.verify(root / "dataset/train", root / args.training_name / "dataset_snapshot.json")
    prediction = lab.read(root / args.prediction)
    assert prediction["model_sha256"] == report["model_sha256"]
    assert prediction["prediction_shape"] == [2, 8, 28]
    assert prediction["label_passed_as_input"] is False and prediction["robot_command_sent"] is False
    sdk = lab.require_sdk()
    ds = sdk.LeRobotDataset(repo_id="handbook/alignment-train", root=root / "dataset/train",
         delta_timestamps={"action": [i / 10 for i in range(8)]}, video_backend="pyav")
    mask = ds[len(ds)-1]["action_is_pad"].tolist()
    assert mask == [False] + [True] * 7
    log = (root / (args.training_name + ".log")).read_text()
    losses = [{"step": int(s), "total": float(t), "l1": float(l), "kl": float(k)} for s,t,l,k in
              re.findall(r"step:(\d+).*?loss:([\d.]+).*?l1_loss:([\d.]+).*?kld_loss:([\d.]+)", log)]
    assert len(losses) == report["steps"]
    evidence = {"checked_on": "2026-10-18", "lab_code_sha256": lab.digest(lab.__file__),
                "sdk_commit": lab.SDK_COMMIT, "environment": {k:report["resources_before"][k] for k in
                ("python", "platform", "lerobot", "torch", "torchvision", "numpy", "pyarrow", "accelerate")},
                "real_source": {"repo_id": download["repo_id"], "revision": download["revision"],
                    "bytes": download["total_bytes"], "files": len(download["files"]),
                    "numeric_shapes": real["shapes"], "complete_dataset": False, "videos_downloaded": False},
                "synthetic_export": exported["roles"], "tail_action_padding": mask,
                "training": {"device": report["device"], "steps": report["steps"], "seed": report["seed"],
                    "losses": losses, "model_sha256": report["model_sha256"]},
                "inference": {k:prediction[k] for k in ("prediction_shape", "input_keys", "label_passed_as_input", "robot_command_sent")},
                "verified": ["real download hashes", "real numeric arrays", "official SDK export/readback",
                    "episode split", "raw and training snapshots", "tail padding", "official ACT updates", "checkpoint restore"],
                "not_verified": ["fresh OS installation", "CUDA/NPU training", "IsaacLab", "physical teleoperation",
                    "real G1 task competence", "production UI"],
                "thermal_before": report["resources_before"].get("thermal_status"),
                "thermal_after": report["resources_after"].get("thermal_status"),
                "measured_temperature_celsius": None}
    lab.write(args.output, evidence)
    print("Handbook run verified:", args.output)


if __name__ == "__main__": main()
