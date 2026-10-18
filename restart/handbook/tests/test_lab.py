"""Data rejection and provenance behavior; no SDK, network or robot needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("handbook_lab", Path(__file__).parents[1] / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def capture(self):
        path = self.root / "capture"
        lab.make_capture(path)
        return path

    def change(self, root, edit):
        path = root / "episode_0000/data.json"
        value = lab.read(path)
        edit(value["data"])
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_capture_has_explicit_non_robot_scope_and_separate_episodes(self):
        contract, episodes = lab.parse_capture(self.capture())
        self.assertFalse(contract["robot_deployment_authorized"])
        self.assertTrue(contract["synthetic"])
        self.assertEqual(len(episodes), 4)
        self.assertTrue(set(contract["splits"]["train"]).isdisjoint(contract["splits"]["validation"]))

    def test_nonfinite_action_rejected(self):
        root = self.capture()
        self.change(root, lambda rows: rows[0]["actions"]["left_arm"]["qpos"].__setitem__(0, float("nan")))
        with self.assertRaises(ValueError): lab.parse_capture(root)

    def test_wrong_joint_dimension_rejected(self):
        root = self.capture()
        self.change(root, lambda rows: rows[0]["states"]["left_hand"]["qpos"].pop())
        with self.assertRaises(ValueError): lab.parse_capture(root)

    def test_duplicate_time_index_rejected(self):
        root = self.capture()
        self.change(root, lambda rows: rows[1].__setitem__("idx", 0))
        with self.assertRaises(ValueError): lab.parse_capture(root)

    def test_image_cannot_escape_capture_root(self):
        root = self.capture()
        external = self.root / "outside.jpg"
        external.write_bytes(b"not a real camera image")
        self.change(root, lambda rows: rows[0]["colors"].__setitem__("color_0", "../../outside.jpg"))
        with self.assertRaises(ValueError): lab.parse_capture(root)

    def test_missing_camera_frame_rejected(self):
        root = self.capture()
        (root / "episode_0000/colors/000000_color_0.jpg").unlink()
        with self.assertRaises(ValueError): lab.parse_capture(root)

    def test_snapshot_detects_data_change(self):
        root = self.capture(); manifest = self.root / "snapshot.json"
        before = lab.snapshot(root, manifest)
        self.assertEqual(lab.verify(root, manifest), before)
        self.change(root, lambda rows: rows[0]["actions"]["left_arm"]["qpos"].__setitem__(0, 0.45))
        with self.assertRaises(ValueError): lab.verify(root, manifest)

    def test_snapshot_detects_new_file(self):
        root = self.capture(); manifest = self.root / "snapshot.json"
        lab.snapshot(root, manifest)
        (root / "extra.txt").write_text("new", encoding="utf-8")
        with self.assertRaises(ValueError): lab.verify(root, manifest)

    def test_snapshot_must_live_outside_source(self):
        root = self.capture()
        with self.assertRaises(ValueError): lab.snapshot(root, root / "snapshot.json")

    def test_existing_output_not_silently_replaced(self):
        root = self.capture()
        with self.assertRaises(FileExistsError): lab.make_capture(root)


if __name__ == "__main__": unittest.main()
