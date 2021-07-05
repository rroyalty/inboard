from __future__ import annotations

import os
import re
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.applications import Starlette


class TestCors:
    """Test CORS middleware integration.
    ---
    See the [FastAPI CORS tutorial](https://fastapi.tiangolo.com/tutorial/cors/) and
    [Starlette CORS docs](https://www.starlette.io/middleware/#corsmiddleware).
    """

    origins: dict[str, list[str]] = {
        "allowed": [
            "http://br3ndon.land",
            "https://br3ndon.land",
            "https://inboard.br3ndon.land",
            "https://inboard.docker.br3ndon.land",
            "https://www.br3ndon.land",
            "http://localhost:8000",
        ],
        "disallowed": [
            "https://br3ndon.com",
            "https://inboar.dbr3ndon.land",
            "https://example.land",
            "htttp://localhost:8000",
            "httpss://br3ndon.land",
            "othersite.com",
        ],
    }

    @pytest.mark.parametrize("allowed_origin", origins["allowed"])
    def test_cors_preflight_response_allowed(
        self, allowed_origin: str, clients: list[TestClient]
    ) -> None:
        """Test pre-flight response to cross-origin request from allowed origin."""
        headers: dict[str, str] = {
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Example",
        }
        for client in clients:
            response = client.options("/", headers=headers)
            assert response.status_code == 200, response.text
            assert response.text == "OK"
            assert response.headers["access-control-allow-origin"] == allowed_origin
            assert response.headers["access-control-allow-headers"] == "X-Example"

    @pytest.mark.parametrize("disallowed_origin", origins["disallowed"])
    def test_cors_preflight_response_disallowed(
        self, disallowed_origin: str, clients: list[TestClient]
    ) -> None:
        """Test pre-flight response to cross-origin request from disallowed origin."""
        headers: dict[str, str] = {
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Example",
        }
        for client in clients:
            response = client.options("/", headers=headers)
            assert response.status_code >= 400
            assert "Disallowed CORS origin" in response.text
            assert not response.headers.get("access-control-allow-origin")

    @pytest.mark.parametrize("allowed_origin", origins["allowed"])
    def test_cors_response_allowed(
        self, allowed_origin: str, clients: list[TestClient]
    ) -> None:
        """Test response to cross-origin request from allowed origin."""
        headers = {"Origin": allowed_origin}
        for client in clients:
            response = client.get("/", headers=headers)
            assert response.status_code == 200, response.text
            assert response.json() == {"Hello": "World"}
            assert response.headers["access-control-allow-origin"] == allowed_origin

    @pytest.mark.parametrize("disallowed_origin", origins["disallowed"])
    def test_cors_response_disallowed(
        self, disallowed_origin: str, clients: list[TestClient]
    ) -> None:
        """Test response to cross-origin request from disallowed origin.
        As explained in the Starlette test suite in tests/middleware/`test_cors.py`,
        enforcement of CORS allowed origins is the responsibility of the client.
        On the server side, the "disallowed-ness" results in lack of an
        "Access-Control-Allow-Origin" header in the response.
        """
        headers = {"Origin": disallowed_origin}
        for client in clients:
            response = client.get("/", headers=headers)
            assert response.status_code == 200
            assert not response.headers.get("access-control-allow-origin")

    def test_non_cors(self, clients: list[TestClient]) -> None:
        """Test non-CORS response."""
        for client in clients:
            response = client.get("/")
            assert response.status_code == 200, response.text
            assert response.json() == {"Hello": "World"}
            assert "access-control-allow-origin" not in response.headers


class TestEndpoints:
    """Test API endpoints.
    ---
    See the [FastAPI testing docs](https://fastapi.tiangolo.com/tutorial/testing/),
    [Starlette TestClient docs](https://www.starlette.io/testclient/), and the
    [pytest docs](https://docs.pytest.org/en/latest/how-to/parametrize.html).
    """

    def test_get_asgi_uvicorn(
        self, client_asgi: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test `GET` request to base ASGI app set for Uvicorn without Gunicorn."""
        monkeypatch.setenv("PROCESS_MANAGER", "uvicorn")
        monkeypatch.setenv("WITH_RELOAD", "false")
        assert os.getenv("PROCESS_MANAGER") == "uvicorn"
        assert os.getenv("WITH_RELOAD") == "false"
        version = sys.version_info
        response = client_asgi.get("/")
        assert response.status_code == 200
        assert response.text == (
            f"Hello World, from Uvicorn and Python "
            f"{version.major}.{version.minor}.{version.micro}!"
        )

    def test_get_asgi_uvicorn_gunicorn(
        self, client_asgi: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test `GET` request to base ASGI app set for Uvicorn with Gunicorn."""
        monkeypatch.setenv("PROCESS_MANAGER", "gunicorn")
        monkeypatch.setenv("WITH_RELOAD", "false")
        assert os.getenv("PROCESS_MANAGER") == "gunicorn"
        assert os.getenv("WITH_RELOAD") == "false"
        version = sys.version_info
        response = client_asgi.get("/")
        assert response.status_code == 200
        assert response.text == (
            f"Hello World, from Uvicorn, Gunicorn, and Python "
            f"{version.major}.{version.minor}.{version.micro}!"
        )

    def test_get_asgi_incorrect_process_manager(
        self, client_asgi: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test `GET` request to base ASGI app with incorrect `PROCESS_MANAGER`."""
        monkeypatch.setenv("PROCESS_MANAGER", "incorrect")
        monkeypatch.setenv("WITH_RELOAD", "false")
        assert os.getenv("PROCESS_MANAGER") == "incorrect"
        assert os.getenv("WITH_RELOAD") == "false"
        with pytest.raises(NameError) as e:
            client_asgi.get("/")
            assert str(e) == "Process manager needs to be either uvicorn or gunicorn."

    def test_get_root(self, clients: list[TestClient]) -> None:
        """Test a `GET` request to the root endpoint."""
        for client in clients:
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"Hello": "World"}

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_basic_auth(
        self, basic_auth: tuple, clients: list[TestClient], endpoint: str
    ) -> None:
        """Test `GET` requests to endpoints that require HTTP Basic auth."""
        for client in clients:
            assert client.get(endpoint).status_code in [401, 403]
            response = client.get(endpoint, auth=basic_auth)
            assert response.status_code == 200
            assert "application" in response.json().keys()
            assert "status" in response.json().keys()
            assert response.json()["application"] == "inboard"
            assert response.json()["status"] == "active"

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_basic_auth_incorrect(
        self, basic_auth: tuple, clients: list[TestClient], endpoint: str
    ) -> None:
        """Test `GET` requests with incorrect HTTP Basic auth credentials."""
        basic_auth_username, basic_auth_password = basic_auth
        for client in clients:
            assert client.get(endpoint).status_code in [401, 403]
            auth_combos = [
                ("incorrect_username", "incorrect_password"),
                ("incorrect_username", basic_auth_password),
                (basic_auth_username, "incorrect_password"),
            ]
            responses = [client.get(endpoint, auth=combo) for combo in auth_combos]
            assert [response.status_code in [401, 403] for response in responses]
            response = client.get(endpoint, auth=basic_auth)
            assert response.status_code == 200

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_fastapi_auth_incorrect_credentials(
        self, clients: list[TestClient], endpoint: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test FastAPI `GET` requests with incorrect HTTP Basic auth credentials."""
        monkeypatch.setenv("BASIC_AUTH_USERNAME", "test_user")
        monkeypatch.setenv("BASIC_AUTH_PASSWORD", "r4ndom_bUt_memorable")
        fastapi_client = clients[0]
        response = fastapi_client.get(endpoint, auth=("user", "pass"))
        assert isinstance(fastapi_client.app, FastAPI)
        assert response.status_code in [401, 403]
        assert response.json() == {"detail": "HTTP Basic auth credentials not correct"}

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_fastapi_auth_no_credentials(
        self, clients: list[TestClient], endpoint: str
    ) -> None:
        """Test FastAPI `GET` requests without HTTP Basic auth credentials set."""
        fastapi_client = clients[0]
        response = fastapi_client.get(endpoint, auth=("user", "pass"))
        assert isinstance(fastapi_client.app, FastAPI)
        assert response.status_code in [401, 403]
        assert response.json() == {
            "detail": "Server HTTP Basic auth credentials not set"
        }

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_starlette_auth_incorrect_credentials(
        self, clients: list[TestClient], endpoint: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Starlette `GET` requests with incorrect HTTP Basic auth credentials."""
        monkeypatch.setenv("BASIC_AUTH_USERNAME", "test_user")
        monkeypatch.setenv("BASIC_AUTH_PASSWORD", "r4ndom_bUt_memorable")
        starlette_client = clients[1]
        response = starlette_client.get(endpoint, auth=("user", "pass"))
        assert isinstance(starlette_client.app, Starlette)
        assert response.status_code in [401, 403]
        assert response.json() == {
            "detail": "HTTP Basic auth credentials not correct",
            "error": "Incorrect username or password",
        }

    @pytest.mark.parametrize("endpoint", ["/health", "/status"])
    def test_gets_with_starlette_auth_no_credentials(
        self, clients: list[TestClient], endpoint: str
    ) -> None:
        """Test Starlette `GET` requests without HTTP Basic auth credentials set."""
        starlette_client = clients[1]
        response = starlette_client.get(endpoint, auth=("user", "pass"))
        assert isinstance(starlette_client.app, Starlette)
        assert response.status_code in [401, 403]
        assert response.json() == {
            "detail": "Server HTTP Basic auth credentials not set",
            "error": "Incorrect username or password",
        }

    def test_get_status_message(
        self,
        basic_auth: tuple,
        clients: list[TestClient],
        endpoint: str = "/status",
    ) -> None:
        """Test the message returned by a `GET` request to a status endpoint."""
        for client in clients:
            assert client.get(endpoint).status_code in [401, 403]
            response = client.get(endpoint, auth=basic_auth)
            assert response.status_code == 200
            assert "message" in response.json().keys()
            assert "Hello World, from Uvicorn" in response.json()["message"]
            assert [
                word in re.split(r"[!?',;.\s]+", response.json()["message"])
                for word in ["Hello", "World", "Uvicorn", "Python"]
            ]
            if isinstance(client.app, FastAPI):
                assert "FastAPI" in response.json()["message"]
            elif isinstance(client.app, Starlette):
                assert "Starlette" in response.json()["message"]

    def test_get_user(
        self,
        basic_auth: tuple,
        clients: list[TestClient],
        endpoint: str = "/users/me",
    ) -> None:
        """Test a `GET` request to an endpoint providing user information."""
        for client in clients:
            assert client.get(endpoint).status_code in [401, 403]
            response = client.get(endpoint, auth=basic_auth)
            assert response.status_code == 200
            assert "application" not in response.json().keys()
            assert "status" not in response.json().keys()
            assert response.json()["username"] == "test_user"
