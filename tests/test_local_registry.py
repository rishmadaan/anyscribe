"""The local-model registry: every id carries every field, featured order is
fixed, and the ratings reproduce the measured table from the 2026-11-19 spec."""

from __future__ import annotations

import pytest

from anyscribe.providers import local_models as lm

FIELDS = {
    "display_name",
    "engine",
    "en_wer",
    "x_realtime",
    "accuracy",
    "speed",
    "min_per_hour",
    "download_mb",
    "ram_mb",
    "languages",
    "language_codes",
    "use_for",
    "featured",
    "badge",
    "tucked",
}


@pytest.mark.parametrize("model_id", lm.MODEL_SIZES)
def test_every_model_has_every_field(model_id):
    spec = lm.MODEL_SPECS[model_id]
    assert FIELDS <= set(spec), FIELDS - set(spec)
    assert spec["engine"] in {"whisper", "parakeet"}
    assert model_id in lm.MODEL_REPOS
    # a model is either a featured card or tucked away with a reason, never both
    assert bool(spec["featured"]) != bool(spec["tucked"])
    if spec["engine"] == "parakeet":
        assert model_id in lm.ONNX_ASR_NAMES
        assert spec["language_codes"]


def test_whisper_ids_unchanged_and_parakeet_added():
    whisper = {"tiny", "base", "small", "medium", "large-v3", "large-v3-turbo", "distil-large-v3.5"}
    assert set(lm.MODEL_SIZES) == whisper | {"parakeet-v3", "parakeet-v2"}
    assert {m for m in lm.MODEL_SIZES if lm.engine_of(m) == "whisper"} == whisper


def test_featured_order_and_recommended():
    assert lm.featured_models() == ["parakeet-v3", "large-v3-turbo", "small", "base"]
    assert lm.RECOMMENDED_MODEL == "parakeet-v3"
    assert lm.MODEL_SPECS["parakeet-v3"]["badge"] == "recommended"
    assert lm.MODEL_SPECS["large-v3-turbo"]["badge"].startswith("for Hindi")
    assert len([m for m in lm.MODEL_SIZES if not lm.MODEL_SPECS[m]["featured"]]) == 5


def test_display_names():
    assert [lm.display_name(m) for m in lm.MODEL_SIZES] == [
        "Parakeet v3",
        "Whisper Large v3 Turbo",
        "Whisper Small",
        "Whisper Base",
        "Parakeet v2",
        "Whisper Medium",
        "Whisper Large v3",
        "Distil-Whisper Large v3.5",
        "Whisper Tiny",
    ]


# (id, EN WER, x realtime) -> (accuracy, speed, minutes per hour), from spec §0 / §1.5
TABLE = {
    "parakeet-v3": ((6.54, 6.3), (5, 4, 10)),
    "parakeet-v2": ((7.50, 6.5), (4, 4, 9)),
    "large-v3-turbo": ((6.63, 1.5), (5, 2, 40)),
    "large-v3": ((7.19, 0.4), (4, 1, 150)),
    "medium": ((7.28, 0.9), (4, 1, 67)),
    "small": ((7.06, 2.7), (4, 3, 22)),
    "base": ((10.16, 7.8), (3, 4, 8)),
    "tiny": ((11.90, 14.4), (2, 5, 4)),
    "distil-large-v3.5": ((10.01, 1.9), (3, 2, 32)),
}


@pytest.mark.parametrize("model_id", TABLE)
def test_rating_rule_reproduces_measured_table(model_id):
    (wer, xrt), (acc, speed, mph) = TABLE[model_id]
    spec = lm.MODEL_SPECS[model_id]
    assert (spec["en_wer"], spec["x_realtime"]) == (wer, xrt)
    assert (spec["accuracy"], spec["speed"], spec["min_per_hour"]) == (acc, speed, mph)


def test_rating_rule_boundaries():
    assert [lm.accuracy_rating(w) for w in (6.7, 6.71, 7.6, 7.61, 10.5, 10.51)] == [
        5,
        4,
        4,
        3,
        3,
        2,
    ]
    assert [lm.speed_rating(x) for x in (12, 11.9, 6, 5.9, 2.5, 2.4, 1.2, 1.1)] == [
        5,
        4,
        4,
        3,
        3,
        2,
        2,
        1,
    ]


def test_parakeet_v3_language_set():
    assert len(lm.PARAKEET_V3_LANGUAGES) == 25
    assert "en" in lm.PARAKEET_V3_LANGUAGES and "hi" not in lm.PARAKEET_V3_LANGUAGES
    assert lm.MODEL_SPECS["parakeet-v2"]["language_codes"] == ["en"]


def test_parakeet_attribution_ships_in_both_notice_files():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    credit = "Parakeet TDT 0.6B v3** by NVIDIA, CC BY 4.0, converted to ONNX by istupakov"
    for f in ("NOTICE", "src/anyscribe/web/static/THIRD-PARTY-LICENSES.md"):
        text = (root / f).read_text()
        assert credit in text, f
        assert "onnx-asr** by Ilya Stupakov, MIT License" in text, f
