"""Create a tiny, entirely synthetic alignment example; no robot connection."""

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent


def main():
    image_dir = ROOT / "images"
    image_dir.mkdir(exist_ok=True)
    points = [(0.098, 0.049), (0.099, 0.0495), (0.100, 0.050)]
    commands = [(0.001, 0.0005), (0.001, 0.0005), (0.0, 0.0)]
    rows = []

    def project(xy):
        # Fixed station frame: +X right, +Y up. 40 pixels per millimetre.
        return (200 + (xy[0] - 0.099) * 40000,
                130 - (xy[1] - 0.05) * 40000)

    for index, (point, command) in enumerate(zip(points, commands)):
        image_path = f"images/frame_{index:03d}.png"
        img = Image.new("RGB", (400, 260), "#f5f5f0")
        draw = ImageDraw.Draw(img)
        draw.rectangle((20, 20, 380, 240), outline="#c9cdc4", width=2)
        for x in range(40, 380, 40):
            draw.line((x, 40, x, 220), fill="#e4e7df")
        for y in range(50, 240, 40):
            draw.line((40, y, 360, y), fill="#e4e7df")
        hx, hy = project((0.1, 0.05))
        draw.ellipse((hx - 13, hy - 13, hx + 13, hy + 13),
                     outline="#147d55", width=4)
        tx, ty = project(point)
        draw.line((tx - 8, ty, tx + 8, ty), fill="#2459c4", width=4)
        draw.line((tx, ty - 8, tx, ty + 8), fill="#2459c4", width=4)
        img.save(ROOT / image_path)
        rows.append({
            "timestamp_s": index / 10,
            "observation": {"image": image_path, "tool_xy_m": list(point)},
            "action": {"delta_xy_m": list(command)},
        })

    (ROOT / "raw.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
