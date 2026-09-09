"""Tests for Turnkey Infrastructure Orchestration and Mock SAP Gateway."""

import json
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import pytest
from typer.testing import CliRunner

from gl_fuzzer.cli import app
from docker.mock_sap_service import SAPODataHandler, run_server
import socketserver


def test_docker_compose_syntax_and_services():
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists()
    content = compose_path.read_text(encoding="utf-8")
    assert "redpanda" in content
    assert "mock-sap-gateway" in content
    assert "localstack" in content
    assert "gl-fuzzer" in content
    assert "19092" in content
    assert "8000" in content


def test_mock_sap_service_endpoints():
    # Run mock SAP on a dynamic port
    test_port = 8765
    httpd = socketserver.TCPServer(("", test_port), SAPODataHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(0.1)

    try:
        # 1. Health check
        with urllib.request.urlopen(f"http://localhost:{test_port}/health") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "UP"
            assert data["service"] == "SAP_S4HANA_ODATA_GATEWAY_MOCK"

        # 2. CSRF Token & GET entities
        req = urllib.request.Request(f"http://localhost:{test_port}/sap/opu/odata4/sap/api_journalentrycreaterequest/srvd_a2x/sap/journalentrycreaterequest/0001/")
        req.add_header("x-csrf-token", "fetch")
        with urllib.request.urlopen(req) as resp:
            csrf = resp.headers.get("x-csrf-token")
            assert csrf is not None
            data = json.loads(resp.read().decode("utf-8"))
            assert "value" in data
            assert len(data["value"]) >= 1

        # 3. POST Journal Entry Request
        post_data = json.dumps({"CompanyCode": "1000", "FiscalYear": "2026"}).encode("utf-8")
        post_req = urllib.request.Request(
            f"http://localhost:{test_port}/sap/opu/odata4/sap/api_journalentrycreaterequest/srvd_a2x/sap/journalentrycreaterequest/0001/",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(post_req) as resp:
            assert resp.status == 201
            post_res = json.loads(resp.read().decode("utf-8"))
            assert post_res["Status"] == "POSTED_SUCCESS"
            assert post_res["CompanyCode"] == "1000"

    finally:
        httpd.shutdown()
        httpd.server_close()


def test_cli_cluster_status():
    runner = CliRunner()
    res = runner.invoke(app, ["cluster", "status"])
    assert res.exit_code == 0
    assert "Enterprise Cluster Service Status" in res.output
    assert "Redpanda" in res.output
    assert "Mock SAP" in res.output
