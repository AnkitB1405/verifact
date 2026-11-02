"""API contract tests. Owner: P1 (FR-43 to FR-52)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from .conftest import SAMPLE


def _run_to_completion(client: TestClient, text: str = SAMPLE) -> dict[str, Any]:
    accepted = client.post("/api/v1/analyze", json={"text": text, "asof": "2026-11-01"})
    assert accepted.status_code == 202, accepted.text
    run_id = accepted.json()["run_id"]
    # TestClient runs background tasks synchronously when the response closes,
    # so one poll suffices here. The dashboard still polls, because a real
    # server does not behave this way.
    result = client.get(f"/api/v1/results/{run_id}")
    assert result.status_code == 200, result.text
    data: dict[str, Any] = result.json()
    return data


# -- health -------------------------------------------------------------------


def test_health_reports_components_and_active_models(client: TestClient) -> None:
    """FR-46. The *active* backends, so a silent fallback is visible."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    names = {c["name"] for c in body["components"]}
    assert names >= {"source_registry", "database", "calibrator"}
    assert body["model_versions"]["nli"] == "lexical-fallback"
    assert body["config_hash"]


def test_health_needs_no_api_key(authed_client: TestClient) -> None:
    """An ops probe must work without a credential."""
    assert authed_client.get("/api/v1/health").status_code == 200


# -- analyze and results -----------------------------------------------------


def test_analyze_returns_202_with_a_poll_url(client: TestClient) -> None:
    """FR-43: a document is tens of seconds of work, so it cannot be synchronous."""
    response = client.post("/api/v1/analyze", json={"text": SAMPLE})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["poll"] == f"/api/v1/results/{body['run_id']}"


def test_results_available_immediately_after_accept(client: TestClient) -> None:
    """A row must exist before 202 returns, or an eager client gets a 404."""
    run_id = client.post("/api/v1/analyze", json={"text": SAMPLE}).json()["run_id"]
    assert client.get(f"/api/v1/results/{run_id}").status_code == 200


def test_full_run_produces_verdicts_and_annotated_text(client: TestClient) -> None:
    body = _run_to_completion(client)
    run = body["run"]
    assert run["status"] == "done"
    assert run["verdicts"]
    assert run["annotated_text"]
    assert sum(body["status_counts"].values()) == len(run["verdicts"])


def test_run_records_provenance(client: TestClient) -> None:
    """FR-62: without this a result is not reproducible."""
    provenance = _run_to_completion(client)["run"]["provenance"]
    assert provenance["config_hash"]
    assert provenance["model_versions"]
    assert provenance["timings_ms"]["total_ms"] > 0


def test_absent_evidence_is_never_contradicted(client: TestClient) -> None:
    """FR-30 through the API, not only in the aggregation unit."""
    body = _run_to_completion(client, "Zqxthuloa Brennigan invented the flibbertigibbet in 1623.")
    statuses = {v["status"] for v in body["run"]["verdicts"]}
    assert "CONTRADICTED" not in statuses, statuses


def test_unknown_run_is_404_with_a_typed_body(client: TestClient) -> None:
    response = client.get("/api/v1/results/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"


def test_export_is_reimportable_json(client: TestClient) -> None:
    """FR-59."""
    run_id = _run_to_completion(client)["run"]["id"]
    response = client.get(f"/api/v1/results/{run_id}/export")
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["id"] == run_id
    assert body["exported_at"]
    assert body["meta"]["config_hash"]


# -- verify and correct ------------------------------------------------------


def test_verify_is_synchronous_and_explains_itself(client: TestClient) -> None:
    """FR-44, FR-35."""
    response = client.post(
        "/api/v1/verify", json={"claim": "The Eiffel Tower is located in Paris."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"]["status"]
    assert body["explanation"]
    assert body["verdict"]["component_scores"]["evidence_coverage"] is not None


def test_uncalibrated_score_is_never_called_a_probability(client: TestClient) -> None:
    """ADR-005, enforced at the API boundary."""
    body = client.post("/api/v1/verify", json={"claim": "The Eiffel Tower is in Paris."}).json()
    assert body["verdict"]["calibrated"] is False
    assert "not a probability" in body["confidence_note"]


def test_correct_abstains_rather_than_guessing(client: TestClient) -> None:
    """FR-38: abstention is a first-class outcome, not an error."""
    response = client.post("/api/v1/correct", json={"claim": "My neighbours cat is called Mitzi."})
    assert response.status_code == 200
    correction = response.json()["correction"]
    assert correction["abstained"] is True
    assert correction["abstain_reason"]


def test_verify_rejects_text_with_no_checkworthy_claim(client: TestClient) -> None:
    response = client.post("/api/v1/verify", json={"claim": "What a beautiful monument!"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


# -- feedback ----------------------------------------------------------------


def test_feedback_is_stored_against_a_run(client: TestClient) -> None:
    """FR-48."""
    run_id = _run_to_completion(client)["run"]["id"]
    response = client.post(
        "/api/v1/feedback",
        json={"run_id": run_id, "label": "disagree", "comment": "wrong date"},
    )
    assert response.status_code == 201
    assert response.json()["feedback_id"]


def test_feedback_for_an_unknown_run_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/feedback", json={"run_id": "nope", "label": "agree"})
    assert response.status_code == 404


# -- auth and rate limiting --------------------------------------------------


def test_missing_api_key_is_401(authed_client: TestClient) -> None:
    """FR-50."""
    response = authed_client.post("/api/v1/verify", json={"claim": "A fact about Paris."})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_wrong_api_key_is_401(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/verify",
        json={"claim": "A fact about Paris."},
        headers={"X-API-Key": "not-the-key"},
    )
    assert response.status_code == 401


def test_valid_api_key_is_accepted(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/analyze",
        json={"text": SAMPLE},
        headers={"X-API-Key": "test-key-1"},
    )
    assert response.status_code == 202


def test_rate_limit_returns_429(authed_client: TestClient, monkeypatch) -> None:
    """FR-51."""
    from verifact.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings.api, "rate_limit_per_minute", 3)
    headers = {"X-API-Key": "test-key-1"}
    codes = [
        authed_client.post(
            "/api/v1/verify", json={"claim": "The Eiffel Tower is in Paris."}, headers=headers
        ).status_code
        for _ in range(5)
    ]
    assert 429 in codes, codes
    assert codes.count(429) == 2


# -- validation and errors ---------------------------------------------------


def test_empty_text_is_422_not_500(client: TestClient) -> None:
    """FR-02, FR-52."""
    assert client.post("/api/v1/analyze", json={"text": ""}).status_code == 422


def test_oversized_text_is_rejected(client: TestClient) -> None:
    """SR-05."""
    response = client.post("/api/v1/analyze", json={"text": "A fact. " * 20000})
    assert response.status_code in (413, 422)
    assert response.json()["code"] in ("input_too_large", "invalid_input")


def test_unknown_field_is_rejected(client: TestClient) -> None:
    """extra=forbid: a typo in a client payload is an error, not silently ignored."""
    response = client.post("/api/v1/analyze", json={"text": "A fact.", "txet": "oops"})
    assert response.status_code == 422


def test_error_body_has_no_traceback_and_no_echo_of_input(client: TestClient) -> None:
    """FR-52, SR-06. The submitted text is the user's content."""
    secret = "my private medical question about a rare condition"
    response = client.post("/api/v1/verify", json={"claim": secret, "bogus": 1})
    assert response.status_code == 422
    raw = response.text
    assert "Traceback" not in raw
    assert secret not in raw


def test_sql_metacharacters_in_input_are_inert(client: TestClient) -> None:
    """SR-04: the ORM parameterises everything; no SQL is built from strings."""
    payload = "Robert'); DROP TABLE runs;-- was completed in 1889."
    body = _run_to_completion(client, payload)
    assert body["run"]["status"] == "done"
    # The schema survived, so a subsequent request still works.
    assert client.get("/api/v1/health").status_code == 200
    assert client.post("/api/v1/analyze", json={"text": SAMPLE}).status_code == 202


# -- openapi and dashboard ---------------------------------------------------


def test_openapi_exposes_every_required_endpoint(client: TestClient) -> None:
    """FR-49."""
    spec = client.get("/openapi.json").json()
    required = {
        "/api/v1/analyze",
        "/api/v1/verify",
        "/api/v1/correct",
        "/api/v1/health",
        "/api/v1/results/{run_id}",
        "/api/v1/feedback",
    }
    assert required <= set(spec["paths"])


def test_api_is_versioned_in_the_path(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert all(path.startswith("/api/v1/") for path in spec["paths"])


def test_dashboard_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "VeriFact" in response.text


def test_sources_endpoint_exposes_tiers(client: TestClient) -> None:
    body = client.get("/api/v1/sources").json()
    ids = {s["id"] for s in body["sources"]}
    assert {"wikidata", "wikipedia", "unknown"} <= ids
    tiers = {s["id"]: s["reliability_tier"] for s in body["sources"]}
    assert tiers["wikidata"] < tiers["unknown"]
