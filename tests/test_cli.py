import json
from pathlib import Path
from shortforge.cli import main


def test_plan_creates_valid_local_storyboard(tmp_path,capsys):
    out=tmp_path/"story.json"
    main(["plan","--topic","water tower","--output",str(out)])
    assert out.exists()
    assert json.loads(out.read_text())["duration"] == 40
    assert "saved" in capsys.readouterr().out


def test_dry_run_has_no_external_side_effects(tmp_path,capsys):
    from shortforge.director import SAMPLE_PATH
    out=tmp_path/"output"
    main(["run",str(SAMPLE_PATH),"--out",str(out),"--dry-run"])
    log=capsys.readouterr().out
    assert "validated_only" in log
    assert not (out/"draft.mp4").exists()
    assert (out/"captions"/"captions.ass").exists()
