from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_status", ROOT / "scripts" / "render_status.py"
)
assert SPEC is not None and SPEC.loader is not None
render_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_status)


class PublicStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = render_status.load_status()

    def test_checked_in_outputs_are_exactly_generated(self) -> None:
        render_status.validate_status(self.status)
        self.assertEqual(
            (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8"),
            render_status.render_markdown(self.status),
        )
        self.assertEqual(
            (ROOT / "meta.json").read_text(encoding="utf-8"),
            render_status.render_meta(self.status),
        )

    def test_duplicate_completed_slice_is_rejected(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["completed"].append(copy.deepcopy(changed["completed"][-1]))
        with self.assertRaisesRegex(render_status.StatusError, "duplicate completed"):
            render_status.validate_status(changed)

    def test_active_slice_cannot_be_claimed_complete(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["current"]["slice"] = changed["last_completed"]["slice"]
        with self.assertRaisesRegex(render_status.StatusError, "must differ"):
            render_status.validate_status(changed)

    def test_private_repository_link_is_rejected(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["completed"][0]["result"] = (
            "See github.com/kasselvania/generalized_execution_platform for evidence."
        )
        with self.assertRaisesRegex(render_status.StatusError, "prohibited public text"):
            render_status.validate_status(changed)

    def test_last_completed_must_be_final_public_milestone(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["last_completed"]["slice"] = changed["completed"][-2]["slice"]
        changed["reviewed_through"] = changed["completed"][-2]["slice"]
        with self.assertRaisesRegex(render_status.StatusError, "final completed"):
            render_status.validate_status(changed)


if __name__ == "__main__":
    unittest.main()
