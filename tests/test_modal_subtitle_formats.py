import sys
import tempfile
import types
import unittest
from pathlib import Path


class FakeChoice:
    def __init__(self, title: str, value: str, checked: bool = False):
        self.title = title
        self.value = value
        self.checked = checked


modal_stub = types.ModuleType("modal")
questionary_stub = types.ModuleType("questionary")
questionary_stub.Choice = FakeChoice
sys.modules.setdefault("modal", modal_stub)
sys.modules.setdefault("questionary", questionary_stub)

import modal_infer


class Prompt:
    def __init__(self, value):
        self.value = value

    def ask(self):
        return self.value


class FakeQuestionary:
    def __init__(self, input_path: Path):
        self.input_path = input_path
        self.select_answers = iter(["T4", "base"])
        self.checkbox_choices = []
        self.checkbox_validate = None

    def select(self, _message, **_kwargs):
        return Prompt(next(self.select_answers))

    def path(self, _message):
        return Prompt(str(self.input_path))

    def checkbox(self, _message, choices, validate):
        self.checkbox_choices = choices
        self.checkbox_validate = validate
        return Prompt(["lrc"])

    def confirm(self, _message, default=False):
        return Prompt(default)

    def text(self, _message, default=""):
        return Prompt(default)


class ModalSubtitleFormatTests(unittest.TestCase):
    def test_tui_defaults_to_lrc_and_payload_forwards_selected_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "audio.mp3"
            input_path.touch()
            fake_questionary = FakeQuestionary(input_path)
            original_questionary = modal_infer.questionary
            modal_infer.questionary = fake_questionary
            try:
                selection = modal_infer.ask_selection()
            finally:
                modal_infer.questionary = original_questionary

        self.assertEqual(selection.subtitle_formats, ["lrc"])
        self.assertEqual(
            [(choice.value, choice.checked) for choice in fake_questionary.checkbox_choices],
            [("lrc", True), ("vtt", False), ("srt", False)],
        )
        self.assertTrue(fake_questionary.checkbox_validate(["lrc"]))
        self.assertEqual(fake_questionary.checkbox_validate([]), "请至少选择一种字幕格式。")

        selection.subtitle_formats = ["lrc", "srt"]
        manifest = modal_infer.UploadManifest(
            session_id="test",
            source_type="file",
            local_source=Path("audio.mp3"),
            remote_inputs_rel=[Path("sessions/test/input/todo.mp3")],
            remote_output_rel=Path("sessions/test/output"),
            local_output_dir=Path("."),
            remote_logs_rel=Path("sessions/test/logs"),
        )
        payload = modal_infer.build_job_payload(selection, manifest)

        self.assertEqual(payload["sub_formats"], "lrc,srt")
        self.assertEqual(payload["output_suffixes"], [".lrc", ".srt"])
        self.assertEqual(payload["output_targets"][0]["extensions"], [".lrc", ".srt"])


if __name__ == "__main__":
    unittest.main()