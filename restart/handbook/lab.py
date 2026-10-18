"""Independent handbook lab. No robot drivers; all outputs stay in explicit paths."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
SDK_COMMIT = "ca69a2068462a37f7cdcb74180927a2f863d2bf7"
CAMERA = "observation.images.front"
PARTS = ("left_arm", "right_arm", "left_hand", "right_hand")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Use a new output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def files(root):
    return [{"path": str(p.relative_to(root)).replace(os.sep, "/"),
             "bytes": p.stat().st_size, "sha256": digest(p)}
            for p in sorted(Path(root).rglob("*")) if p.is_file()]


def snapshot(root, output):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Put snapshot outside the source directory")
    if not root.is_dir() or not any(root.iterdir()):
        raise ValueError("Source directory is empty or missing")
    entries = files(root)
    release_id = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    write(output, {"schema": "handbook_file_snapshot_v1", "id": release_id,
                   "files": entries, "physical_quality_certified": False})
    return release_id


def verify(root, manifest):
    saved = read(manifest)
    current = files(Path(root))
    if current != saved["files"]:
        raise ValueError("Snapshot mismatch: file added, removed or changed")
    expected = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    if expected != saved["id"]:
        raise ValueError("Snapshot ID mismatch")
    return expected


def doctor():
    result = {"python": sys.version, "executable": sys.executable,
              "platform": platform.platform(), "cpu_count": os.cpu_count(),
              "temperature_celsius": None}
    result["load"] = list(os.getloadavg()) if hasattr(os, "getloadavg") else None
    for name in ("lerobot", "torch", "torchvision", "numpy", "pyarrow", "pillow", "av", "accelerate"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "not installed"
    if sys.platform == "darwin":
        for key, cmd in (("memory_status", ["memory_pressure"]),
                         ("thermal_status", ["pmset", "-g", "therm"])):
            result[key] = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    elif sys.platform.startswith("linux"):
        result["memory_status"] = Path("/proc/meminfo").read_text()
        result["thermal_status"] = "Check OS/vendor monitor; temperature not measured here"
    else:
        result["memory_status"] = "Check Task Manager before sustained work"
        result["thermal_status"] = "Not measured"
    return result


def require_sdk():
    import av
    av.logging.set_level(av.logging.ERROR)
    import torch
    torch.set_num_threads(1)
    import lerobot.datasets.lerobot_dataset as sdk
    checkout = next((p for p in Path(sdk.__file__).resolve().parents if (p / ".git").exists()), None)
    actual = (subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
              if checkout else None)
    if actual != SDK_COMMIT:
        raise ValueError(f"This lab requires editable SDK checkout {SDK_COMMIT}; found {actual}")
    return sdk


def fetch_real(output):
    plan = read(HERE / "sources.lock.json")["real_dataset"]
    output = Path(output)
    if output.exists():
        raise FileExistsError("Use a new download directory")
    output.mkdir(parents=True)
    receipt = []
    total = 0
    for item in plan["files"]:
        path = output / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/datasets/{plan['repo_id']}/resolve/{plan['revision']}/{item['path']}"
        with urllib.request.urlopen(url, timeout=45) as response, path.open("xb") as handle:
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                total += len(block)
                if size > item["bytes"] or total > plan["download_budget_bytes"]:
                    raise ValueError("Download exceeds pinned file size/budget")
                handle.write(block)
        if size != item["bytes"]:
            raise ValueError("Incomplete source download")
        sha = digest(path)
        if sha != item["sha256"]:
            raise ValueError("Source SHA256 mismatch")
        receipt.append({**item, "url": url})
        print("Downloaded:", item["path"], size, flush=True)
    write(output / "download_receipt.json", {"repo_id": plan["repo_id"], "revision": plan["revision"],
          "files": receipt, "total_bytes": total, "complete_dataset": False,
          "videos_downloaded": False, "purpose": "real published schema and tabular records only"})


def inspect_real(root):
    import numpy as np
    import pyarrow.parquet as pq
    root = Path(root)
    receipt = read(root / "download_receipt.json")
    for item in receipt["files"]:
        if digest(root / item["path"]) != item["sha256"]:
            raise ValueError("Downloaded source changed")
    path = root / "data/chunk-000/file-001.parquet"
    table = pq.read_table(path)
    row = table.slice(0, 1).to_pylist()[0]
    shapes = {}
    for key in ("observation.state", "action"):
        values = np.asarray(table[key].to_pylist(), dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != 28 or not np.isfinite(values).all():
            raise ValueError("Published table has unexpected/nonfinite numeric features")
        shapes[key] = list(values.shape)
    info = read(root / "meta/info.json")
    return {"source": receipt["repo_id"], "revision": receipt["revision"],
            "codebase_version": info["codebase_version"], "fps": info["fps"],
            "columns": table.column_names, "shapes": shapes, "first_row": row,
            "state_names": info["features"]["observation.state"]["names"],
            "camera_keys": [k for k in info["features"] if k.startswith("observation.images.")],
            "complete_dataset": False, "images_loaded": False, "ready_for_training": False,
            "units_warning": "feature names alone do not establish command units or control semantics"}


def make_capture(output):
    import numpy as np
    from PIL import Image, ImageDraw
    root = Path(output)
    if root.exists():
        raise FileExistsError("Use a new capture directory")
    root.mkdir(parents=True)
    for ep in range(4):
        folder = root / f"episode_{ep:04d}"
        (folder / "colors").mkdir(parents=True)
        rows = []
        for index in range(20):
            state = np.asarray([0.1 * math.sin(index / 8 + j / 5 + ep / 7) for j in range(28)])
            action = state + 0.01 * np.cos(np.arange(28) / 5 + index / 8)
            img = Image.new("RGB", (64, 64), (24, 32, 40))
            draw = ImageDraw.Draw(img)
            draw.ellipse((40, 25, 49, 34), outline=(30, 210, 120), width=2)
            x = 10 + index
            draw.rectangle((x, 28, x + 3, 31), fill=(80, 120, 240))
            relative = f"colors/{index:06d}_color_0.jpg"
            img.save(folder / relative)
            rows.append({"idx": index, "colors": {"color_0": relative},
                         "states": {part: {"qpos": state[n*7:(n+1)*7].tolist()} for n, part in enumerate(PARTS)},
                         "actions": {part: {"qpos": action[n*7:(n+1)*7].tolist()} for n, part in enumerate(PARTS)}})
        write(folder / "data.json", {"info": {"image": {"fps": 10}},
              "text": {"goal": "Teaching only: synthetic tool alignment"}, "data": rows})
    write(root / "capture_contract.json", {"synthetic": True, "physics_simulation": False,
          "schema": "handbook_unitree_shaped_subset_v1", "parts_order": list(PARTS),
          "dimensions_per_part": 7, "fps": 10, "timestamp_source": "nominal_idx_div_fps",
          "units": "dimensionless teaching signals; not calibrated robot joint commands",
          "splits": {"train": [0, 1, 2], "validation": [3]}, "robot_deployment_authorized": False})


def parse_capture(root):
    import numpy as np
    root = Path(root).resolve()
    contract = read(root / "capture_contract.json")
    if contract["synthetic"] is not True or contract["parts_order"] != list(PARTS):
        raise ValueError("This adapter accepts only the explicit teaching contract")
    episodes = []
    for index in range(4):
        folder = root / f"episode_{index:04d}"
        data = read(folder / "data.json")
        if data["info"]["image"]["fps"] != contract["fps"] or len(data["data"]) != 20:
            raise ValueError("Teaching cadence/length mismatch")
        rows = []
        for t, row in enumerate(data["data"]):
            if row["idx"] != t:
                raise ValueError("Nonsequential frame index")
            values = {}
            for category in ("states", "actions"):
                if any(len(row[category][part]["qpos"]) != 7 for part in PARTS):
                    raise ValueError("Joint part size mismatch")
                value = np.asarray([v for part in PARTS for v in row[category][part]["qpos"]], dtype=np.float32)
                if value.shape != (28,) or not np.isfinite(value).all():
                    raise ValueError("Invalid state/action")
                values[category] = value
            path = (folder / row["colors"]["color_0"]).resolve()
            if root not in path.parents or not path.is_file():
                raise ValueError("Image missing or outside capture root")
            rows.append({**values, "image": path})
        episodes.append((data["text"]["goal"], rows))
    return contract, episodes


def export_capture(capture, output):
    sdk = require_sdk()
    import numpy as np
    from PIL import Image
    from lerobot.configs.video import RGBEncoderConfig
    root = Path(output)
    if root.exists():
        raise FileExistsError("Use a new dataset export directory")
    contract, episodes = parse_capture(capture)
    root.mkdir(parents=True)
    names = [f"{part}_{i}" for part in PARTS for i in range(7)]
    features = {"observation.state": {"dtype": "float32", "shape": (28,), "names": names},
                "action": {"dtype": "float32", "shape": (28,), "names": names},
                CAMERA: {"dtype": "video", "shape": (64, 64, 3), "names": ["height", "width", "channels"]}}
    reports = {}
    for role, indices in contract["splits"].items():
        ds = sdk.LeRobotDataset.create(repo_id=f"handbook/alignment-{role}", root=root / role,
             fps=contract["fps"], robot_type="teaching_signals_not_robot_data", features=features,
             image_writer_processes=0, image_writer_threads=1, encoder_threads=1,
             rgb_encoder=RGBEncoderConfig(vcodec="h264", preset="veryfast", video_backend="pyav"))
        for index in indices:
            goal, rows = episodes[index]
            for row in rows:
                with Image.open(row["image"]) as img:
                    image = np.asarray(img.convert("RGB"))
                ds.add_frame({"observation.state": row["states"], "action": row["actions"],
                              CAMERA: image, "task": goal})
            ds.save_episode(parallel_encoding=False)
        ds.finalize()
        loaded = sdk.LeRobotDataset(repo_id=f"handbook/alignment-{role}", root=root / role, video_backend="pyav")
        expected = len(indices) * 20
        if len(loaded) != expected:
            raise ValueError("Official reader count mismatch")
        for i in range(expected):
            source = episodes[indices[i // 20]][1][i % 20]
            row = loaded[i]
            if not np.allclose(row["action"].numpy(), source["actions"], atol=1e-7):
                raise ValueError("Source/action readback mismatch")
        reports[role] = {"episodes": indices, "frames": len(loaded),
                         "codebase_version": loaded.meta.info.codebase_version,
                         "state_shape": list(loaded[0]["observation.state"].shape),
                         "action_shape": list(loaded[0]["action"].shape),
                         "image_shape": list(loaded[0][CAMERA].shape)}
    snapshot(capture, root / "source_snapshot.json")
    write(root / "export_receipt.json", {"synthetic": True, "official_sdk_commit": SDK_COMMIT,
          "roles": reports, "adapter": "our teaching adapter, not Unitree's official converter",
          "robot_deployment_authorized": False})
    return reports


def batch(root):
    sdk = require_sdk()
    from torch.utils.data import DataLoader
    ds = sdk.LeRobotDataset(repo_id="handbook/alignment-train", root=Path(root) / "train",
         delta_timestamps={"action": [i / 10 for i in range(8)]}, video_backend="pyav")
    result = next(iter(DataLoader(ds, batch_size=2, num_workers=0, shuffle=False)))
    return {"tensor_shapes": {k: list(v.shape) for k, v in result.items() if hasattr(v, "shape")},
            "first_state": result["observation.state"][0].tolist(),
            "first_action_label": result["action"][0, 0].tolist(),
            "first_padding_mask": result["action_is_pad"][0].tolist(),
            "synthetic": True, "normalization": "native values; policy preprocessor applies statistics"}


def train(root, output, device, steps):
    require_sdk()
    if Path(output).exists():
        raise FileExistsError("Use a new trainer output directory")
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    command = [sys.executable, "-m", "lerobot.scripts.lerobot_train",
       "--dataset.repo_id=handbook/alignment-train", f"--dataset.root={Path(root).resolve() / 'train'}",
       "--dataset.video_backend=pyav", "--policy.type=act", f"--policy.device={device}",
       "--policy.push_to_hub=false", "--policy.pretrained_backbone_weights=null",
       "--policy.chunk_size=8", "--policy.n_action_steps=8", "--policy.dim_model=64",
       "--policy.n_heads=4", "--policy.dim_feedforward=128", "--policy.n_encoder_layers=1",
       "--policy.n_decoder_layers=1", "--policy.n_vae_encoder_layers=1", "--policy.latent_dim=8",
       "--batch_size=2", "--num_workers=0", f"--steps={steps}", f"--save_freq={steps}",
       "--seed=1000",
       "--log_freq=1", "--env_eval_freq=0", "--eval_steps=0", "--wandb.enable=false",
       f"--output_dir={Path(output).resolve()}"]
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    log = target.parent / (target.name + ".log")
    if log.exists():
        raise FileExistsError("Use a new training log")
    before = doctor()
    source_before = files(Path(root) / "train")
    with log.open("w", encoding="utf-8") as handle:
        result = subprocess.run(command, env=env, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Official trainer failed; read {log}")
    model = target / f"checkpoints/{steps:06d}/pretrained_model/model.safetensors"
    if not model.is_file():
        raise ValueError("Trainer returned without expected checkpoint")
    if files(Path(root) / "train") != source_before:
        raise ValueError("Training source changed during run")
    snapshot(Path(root) / "train", target / "dataset_snapshot.json")
    write(target / "lab_receipt.json", {"command": command[1:], "synthetic": True,
          "steps": steps, "device": device, "sdk_commit": SDK_COMMIT,
          "lab_code_sha256": digest(__file__), "seed": 1000,
          "checkpoint": str(model.parent), "model_sha256": digest(model), "log_sha256": digest(log),
          "resources_before": before, "resources_after": doctor(), "robot_command_sent": False})
    return {"checkpoint": str(model.parent), "log": str(log)}


def infer(root, checkpoint):
    sdk = require_sdk()
    import torch
    from lerobot.policies.act.modeling_act import ACTPolicy
    from lerobot.policies import make_pre_post_processors
    from torch.utils.data import DataLoader
    checkpoint = Path(checkpoint).resolve()
    receipt = read(checkpoint.parents[2] / "lab_receipt.json")
    if digest(checkpoint / "model.safetensors") != receipt["model_sha256"]:
        raise ValueError("Checkpoint differs from recorded training result")
    verify(Path(root) / "train", checkpoint.parents[2] / "dataset_snapshot.json")
    ds = sdk.LeRobotDataset(repo_id="handbook/alignment-validation", root=Path(root) / "validation", video_backend="pyav")
    row = next(iter(DataLoader(ds, batch_size=2, num_workers=0)))
    policy = ACTPolicy.from_pretrained(str(checkpoint))
    policy.to("cpu").eval()
    policy.config.device = "cpu"
    pre, post = make_pre_post_processors(policy.config, pretrained_path=str(checkpoint),
               preprocessor_overrides={"device_processor": {"device": "cpu"}})
    inputs = {key: row[key] for key in policy.config.input_features}
    with torch.no_grad():
        prediction = post(policy.predict_action_chunk(pre(inputs)))
    if not bool(torch.isfinite(prediction).all()):
        raise ValueError("Nonfinite prediction")
    return {"input_keys": list(inputs), "prediction_shape": list(prediction.shape),
            "first_prediction": prediction[0, 0].tolist(),
            "first_reference_action": row["action"][0].tolist(),
            "label_passed_as_input": False, "robot_command_sent": False,
            "synthetic": True, "model_sha256": digest(Path(checkpoint) / "model.safetensors")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    for name in ("fetch-real", "make-capture"):
        sub.add_parser(name).add_argument("--output", type=Path, required=True)
    q = sub.add_parser("inspect-real"); q.add_argument("--root", type=Path, required=True)
    for name in ("snapshot", "verify"):
        q = sub.add_parser(name); q.add_argument("--root", type=Path, required=True)
        q.add_argument("--manifest" if name == "verify" else "--output", type=Path, required=True)
    q = sub.add_parser("export"); q.add_argument("--capture", type=Path, required=True); q.add_argument("--output", type=Path, required=True)
    for name in ("batch", "train", "infer"):
        q = sub.add_parser(name); q.add_argument("--root", type=Path, required=True)
        if name == "train":
            q.add_argument("--output", type=Path, required=True); q.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
            q.add_argument("--steps", type=int, default=5)
        if name == "infer":
            q.add_argument("--checkpoint", type=Path, required=True)
            q.add_argument("--output", type=Path, help="Optional UTF-8 JSON result; avoids shell encoding differences")
    args = p.parse_args()
    if args.command == "doctor": result = doctor()
    elif args.command == "fetch-real": result = fetch_real(args.output)
    elif args.command == "inspect-real": result = inspect_real(args.root)
    elif args.command == "make-capture": result = make_capture(args.output)
    elif args.command == "snapshot": result = snapshot(args.root, args.output)
    elif args.command == "verify": result = verify(args.root, args.manifest)
    elif args.command == "export": result = export_capture(args.capture, args.output)
    elif args.command == "batch": result = batch(args.root)
    elif args.command == "train":
        if not 1 <= args.steps <= 1000: raise ValueError("Teaching run requires 1..1000 steps")
        result = train(args.root, args.output, args.device, args.steps)
    else:
        with contextlib.redirect_stdout(sys.stderr):
            result = infer(args.root, args.checkpoint)
        if args.output:
            write(args.output, result)
    if result is not None: print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
