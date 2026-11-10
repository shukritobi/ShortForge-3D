"""Seeded asset catalog and reusable library identifiers."""
import copy
import json
import pytest
from shortforge.library import load_catalog
from shortforge.cli import parser


def test_catalog_seed_resolves_sources():
    result=load_catalog()
    assert len(result["entries"]) >= 8
    assert {x["kind"] for x in result["entries"]} >= {"model","action","environment","camera"}


def test_catalog_rejects_duplicate_version(tmp_path):
    data=load_catalog()
    data=copy.deepcopy(data)
    data["entries"].append(data["entries"][0])
    path=tmp_path/"bad.json"
    path.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="Duplicate"):
        load_catalog(path)


def test_catalog_rejects_escape_paths(tmp_path):
    data=copy.deepcopy(load_catalog())
    data["entries"][0]["source"]="../untrusted.py"
    path=tmp_path/"bad.json"
    path.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="outside"):
        load_catalog(path)


def test_cli_exposes_provider_choices():
    args=parser().parse_args(["run","--tts","qwen","--voice","Ryan"])
    assert args.tts=="qwen"
    assert args.voice=="Ryan"
    alt=parser().parse_args(["run","--tts","kokoro","--voice","af_heart"])
    assert alt.tts=="kokoro"
