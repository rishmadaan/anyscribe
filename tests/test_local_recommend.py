"""recommend(): the guided "help me choose" rules and the sentences they produce."""

from __future__ import annotations

import pytest

from anyscribe.core.local_recommend import (
    LANGUAGE_ANSWERS,
    detect_hardware,
    parakeet_suggestion,
    recommend,
)


def hw(ram=16.0, disk=100_000):
    return {
        "ram_gb": ram,
        "cpu_cores": 12,
        "apple_silicon": False,
        "nvidia_gpu": False,
        "free_disk_mb": disk,
    }


@pytest.mark.parametrize("answer", ["english", "european"])
def test_english_and_european_get_parakeet(answer):
    r = recommend(answer, hw())
    assert (r["primary"], r["also"]) == ("parakeet-v3", [])
    assert r["reasons"][0].startswith("You said mostly")
    text = " ".join(r["reasons"])
    assert "as accurate as Whisper Large v3 Turbo" in text
    assert "about 4 times faster on our test desktop" in text
    assert "memory" not in text  # memory didn't change this pick, so it isn't cited
    assert r["reasons"][-1] == "Downloads 670 MB, plus the 75 MB language check."


def test_english_reason_is_plain():
    r = recommend("english", hw())
    assert r["reasons"][1] == (
        "Parakeet v3 is as accurate as Whisper Large v3 Turbo on English, and about "
        "4 times faster on our test desktop."
    )


def test_hindi_gets_turbo_and_the_set_language_offer():
    r = recommend("indian", hw(ram=8))
    assert (r["primary"], r["also"], r["set_language"]) == ("large-v3-turbo", [], "hi")
    text = " ".join(r["reasons"])
    assert "most accurate local model on Hindi" in text
    assert "about 3 times more accurate on Hindi when it is told the language" in text


def test_something_else_has_its_own_reason_without_hindi():
    r = recommend("other", hw(ram=8))
    assert (r["primary"], r["set_language"]) == ("large-v3-turbo", None)
    text = " ".join(r["reasons"])
    assert "95+ languages" in text and "Hindi" not in text


def test_hindi_on_a_small_machine_gets_small_and_says_why():
    r = recommend("indian", hw(ram=5))
    assert r["primary"] == "small"
    assert "this computer has 5 GB" in r["reasons"][1]


def test_mix_gets_parakeet_plus_turbo_with_sizes_and_the_hinglish_line():
    r = recommend("mix", hw())
    assert (r["primary"], r["also"]) == ("parakeet-v3", ["large-v3-turbo"])
    text = " ".join(r["reasons"])
    assert "start, middle and end of each recording" in text
    assert (
        "If one recording switches language mid-sentence (Hinglish), make Whisper Large "
        "v3 Turbo your default instead." in text
    )
    assert r["reasons"][-1] == "Downloads 670 MB + 1.6 GB, plus the 75 MB language check."
    assert r["download_mb"] == 670 + 1600 + 75


@pytest.mark.parametrize("answer", list(LANGUAGE_ANSWERS))
def test_under_4gb_ram_gets_base_for_any_language(answer):
    r = recommend(answer, hw(ram=3))
    assert (r["primary"], r["also"]) == ("base", [])
    assert "3 GB of memory" in r["reasons"][1]


def test_low_disk_steps_down_and_reasons_describe_the_final_pick():
    # parakeet 670 + tiny 75 = 745 MB needed (x1.1 headroom); 600 MB free
    r = recommend("english", hw(disk=600))
    assert r["primary"] == "small"
    text = " ".join(r["reasons"])
    assert "Only 600 MB of disk space is free, not enough for Parakeet v3" in text
    assert "as accurate as" not in text and "language check" not in text
    assert r["reasons"][-1] == "Downloads 460 MB."


def test_low_disk_mix_keeps_a_multilingual_model_instead_of_parakeet_alone():
    r = recommend("mix", hw(disk=2000))
    assert (r["primary"], r["also"]) == ("large-v3-turbo", [])
    r = recommend("mix", hw(disk=1500))
    assert (r["primary"], r["also"]) == ("small", [])
    text = " ".join(r["reasons"])
    assert "two models" not in text and "switches" not in text


def test_nothing_fits_says_not_enough_space_and_how_much():
    r = recommend("english", hw(disk=10))
    assert r["primary"] is None and r["also"] == []
    assert r["reasons"] == [
        "Not enough free disk space: only 10 MB is free, and even the smallest suitable "
        "model (Whisper Base) needs about 154 MB. Free up space, then ask again."
    ]


def test_already_downloaded_models_need_no_disk():
    r = recommend("english", hw(disk=10), cached={"parakeet-v3", "tiny"})
    assert r["primary"] == "parakeet-v3" and r["reasons"][-1] == "Already downloaded."


def test_every_recommendation_is_two_to_five_sentences():
    for answer in LANGUAGE_ANSWERS:
        for ram in (3, 5, 16):
            for disk in (600, 2000, 100_000):
                r = recommend(answer, hw(ram=ram, disk=disk))
                assert 2 <= len(r["reasons"]) <= 5, (answer, ram, disk, r["reasons"])


def test_unknown_answer_rejected():
    with pytest.raises(ValueError):
        recommend("klingon", hw())


def test_detect_hardware_reads_this_machine():
    h = detect_hardware()
    assert set(h) == {"ram_gb", "cpu_cores", "apple_silicon", "nvidia_gpu", "free_disk_mb"}
    assert h["cpu_cores"] and h["cpu_cores"] >= 1


def test_parakeet_suggestion_only_for_whisper_users_on_english_or_auto():
    assert "parakeet-v3" in parakeet_suggestion("large-v3-turbo", "auto")
    assert parakeet_suggestion("base", "en") is not None
    assert parakeet_suggestion("base", "hi") is None
    assert parakeet_suggestion("parakeet-v3", "auto") is None
    assert parakeet_suggestion("gibberish", "auto") is None


def test_web_recommend_route_and_status_fields():
    from fastapi.testclient import TestClient

    from anyscribe.web.app import create_app

    client = TestClient(create_app())
    r = client.get("/api/local/recommend", params={"answer": "mix"})
    assert r.status_code == 200
    body = r.json()
    assert body["primary"] == "parakeet-v3" or body["primary"] in {"small", "base"}
    assert body["reasons"] and body["hardware"]["cpu_cores"]
    assert client.get("/api/local/recommend", params={"answer": "x"}).status_code == 400
    status = client.get("/api/local/status").json()
    assert status["featured"] == ["parakeet-v3", "large-v3-turbo", "small", "base"]
    assert set(status["language_answers"]) == set(LANGUAGE_ANSWERS)
    assert "suggestion" in status and "runtime_ready" in status


def test_mcp_doctor_has_the_local_block(monkeypatch):
    import json

    pytest.importorskip("mcp", reason="mcp extra not installed")
    from anyscribe.mcp import server

    local = json.loads(server.doctor())["local"]
    assert local["recommended_model"] == "parakeet-v3"
    assert set(local["recommendations"]) == set(LANGUAGE_ANSWERS)
    assert local["recommendations"]["english"]["reasons"]


def test_cli_local_status_json_has_recommendations():
    import json

    from typer.testing import CliRunner

    from anyscribe.cli.local_cmd import local_app

    out = CliRunner().invoke(local_app, ["status", "--json"])
    data = json.loads(out.stdout)
    assert set(data["recommendations"]) == set(LANGUAGE_ANSWERS)
    assert data["recommendations"]["indian"]["primary"] in {"large-v3-turbo", "small", "base"}


def test_registry_route_is_plain_data_without_a_disk_scan(monkeypatch):
    from fastapi.testclient import TestClient

    from anyscribe.web.app import create_app
    from anyscribe.web.routes import local as routes

    def boom():
        raise AssertionError("registry must not scan the model cache")

    monkeypatch.setattr(routes, "list_cached_models", boom)
    monkeypatch.setattr(routes, "check_status", boom)
    body = TestClient(create_app()).get("/api/local/registry").json()
    assert body["recommended_model"] == "parakeet-v3"
    pk = body["specs"]["parakeet-v3"]
    assert (pk["display_name"], pk["download_mb"], pk["min_per_hour"]) == ("Parakeet v3", 670, 10)
    assert body["benchmark_caption"].startswith("Speed and accuracy measured on English audio")


def test_hindi_advice_is_conditional_and_says_it_applies_to_every_recording():
    """R2F2: the answer covers every Indian language; the advice is for Hindi audio."""
    text = " ".join(recommend("indian", hw(ram=8))["reasons"])
    assert (
        "If your audio is Hindi, set your language to Hindi: Turbo is about 3 times more "
        "accurate on Hindi when it is told the language. Every recording is then treated "
        "as Hindi." in text
    )
    assert "Set your language to Hindi:" not in text


def test_mix_says_why_parakeet_is_the_main_model():
    text = " ".join(recommend("mix", hw())["reasons"])
    assert "Parakeet v3 is the main one because it is about 4 times faster on English." in text
