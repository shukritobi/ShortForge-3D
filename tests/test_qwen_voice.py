"""Guard voice names against capitalization mismatches in Qwen."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def resolve():
    path = Path(__file__).resolve().parents[1] / "scripts" / "tts_generate.py"
    spec = spec_from_file_location("shortforge_tts_worker", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_voice


def test_qwen_ryan_case_insensitive():
    assert resolve()("Ryan", ["aiden", "ryan"]) == "ryan"


def test_qwen_none_supported():
    assert resolve()("Ryan", None) == "Ryan"


def test_unknown_speaker_rejected():
    with pytest.raises(ValueError, match="unavailable"):
        resolve()("nonexistent", ["aiden", "ryan"])
