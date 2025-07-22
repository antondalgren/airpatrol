"""Test the AirPatrol API client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession

from airpatrol.api import (
    AirPatrolAPI,
    AirPatrolAuthenticationError,
    AirPatrolError,
)


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock aiohttp session."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def api(mock_session: MagicMock) -> AirPatrolAPI:
    """Create AirPatrol API instance."""
    return AirPatrolAPI(mock_session, "test_access_token", "test_user_id")


@pytest.mark.asyncio
async def test_authenticate_success(mock_session: MagicMock) -> None:
    """Test successful authentication."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "status": "ok",
        "entities": {
            "users": {
                "list": [
                    {
                        "id": "test_user_id",
                    }
                ]
            }
        },
        "misc": {"accessToken": "test_access_token"},
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response

    api = await AirPatrolAPI.authenticate(mock_session, "test@example.com", "password")

    assert api._access_token == "test_access_token"
    assert api._user_id == "test_user_id"


@pytest.mark.asyncio
async def test_authenticate_failure_status(mock_session: MagicMock) -> None:
    """Test authentication failure with non-200 status."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.text.return_value = "Unauthorized"
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with pytest.raises(AirPatrolAuthenticationError, match="Authentication failed"):
        await AirPatrolAPI.authenticate(mock_session, "test@example.com", "password")


@pytest.mark.asyncio
async def test_authenticate_failure_exception(mock_session: MagicMock) -> None:
    """Test authentication failure with exception."""
    mock_session.post.side_effect = Exception("Connection error")

    with pytest.raises(Exception, match="Connection error"):
        await AirPatrolAPI.authenticate(mock_session, "test@example.com", "password")


@pytest.mark.asyncio
async def test_get_unique_id_authenticated(api: AirPatrolAPI) -> None:
    """Test getting unique ID when authenticated."""
    assert api.get_unique_id() == "test_user_id"


@pytest.mark.asyncio
async def test_get_access_token_authenticated(api: AirPatrolAPI) -> None:
    """Test getting access token after authentication."""
    assert api.get_access_token() == "test_access_token"


@pytest.mark.asyncio
async def test_get_pairings_success(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test successful pairings fetch."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "status": "ok",
        "entities": {
            "pairingUser": {
                "list": [
                    {"userId": "test_user_id", "pairingId": "00000", "id": "000011"}
                ]
            },
            "pairings": {
                "list": [
                    {
                        "id": "00000",
                        "appId": "00000-00000-00000-00000-00000",
                        "cid": "00000",
                        "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                        "name": "Test Device",
                        "type": "apw",
                    }
                ]
            },
        },
        "misc": {},
        "errors": [],
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    data = await api.get_pairings()

    assert data["status"] == "ok"
    assert "entities" in data
    assert "pairingUser" in data["entities"]
    assert "pairings" in data["entities"]


@pytest.mark.asyncio
async def test_get_pairings_failure_status(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test pairings fetch failure with non-200 status."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.text.return_value = "Unauthorized"
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(AirPatrolAuthenticationError, match="Failed to fetch pairings"):
        await api.get_pairings()


@pytest.mark.asyncio
async def test_get_pairings_failure_error_status(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test pairings fetch failure with error status in response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "error", "errors": ["Invalid token"]}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    with pytest.raises(AirPatrolError, match="API returned error status"):
        await api.get_pairings()


@pytest.mark.asyncio
async def test_get_devices_success(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test successful devices fetch."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "status": "ok",
        "entities": {
            "pairingUser": {
                "list": [
                    {"userId": "test_user_id", "pairingId": "00000", "id": "000011"}
                ]
            },
            "pairings": {
                "list": [
                    {
                        "id": "00000",
                        "appId": "00000-00000-00000-00000-00000",
                        "cid": "00000",
                        "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                        "name": "Test Device",
                        "type": "apw",
                    }
                ]
            },
        },
        "misc": {},
        "errors": [],
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    devices = await api.get_devices()

    assert len(devices) == 1
    device = devices[0]
    assert device["id"] == "00000"
    assert device["name"] == "Test Device"
    assert device["type"] == "apw"
    assert device["hwid"] == "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"


@pytest.mark.asyncio
async def test_get_devices_no_user_pairings(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test devices fetch when user has no pairings."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "status": "ok",
        "entities": {
            "pairingUser": {
                "list": [
                    {
                        "userId": "other_user_id",  # Different user
                        "pairingId": "00000",
                        "id": "000011",
                    }
                ]
            },
            "pairings": {
                "list": [
                    {
                        "id": "00000",
                        "appId": "00000-00000-00000-00000-00000",
                        "cid": "00000",
                        "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                        "name": "Vardagsrum",
                        "type": "apw",
                    }
                ]
            },
        },
        "misc": {},
        "errors": [],
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    devices = await api.get_devices()

    assert len(devices) == 0


# Helper for aiohttp context manager mock
class MockAiohttpResponse:
    """Mock aiohttp response."""

    def __init__(
        self, status: int, json_data: Any | None = None, text_data: Any | None = None
    ) -> None:
        """Initialize mock aiohttp response."""
        self.status = status
        self._json = json_data
        self._text = text_data or ""
        self.url = "mock://url"

    async def __aenter__(self) -> "MockAiohttpResponse":
        """Enter aiohttp context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        """Exit aiohttp context manager."""
        return False

    async def json(self) -> Any:
        """Return JSON data."""
        return self._json

    async def text(self) -> Any:
        """Return text data."""
        return self._text


@pytest.mark.asyncio
async def test_get_data_success(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test successful data fetch."""

    def _mock_get(url: str, *args: Any, **kwargs: Any) -> MockAiohttpResponse:
        if "pairings" in url:
            return MockAiohttpResponse(
                200,
                json_data={
                    "entities": {
                        "pairingUser": {
                            "list": [
                                {
                                    "userId": "11111",
                                    "pairingId": "00000",
                                    "id": "000011",
                                }
                            ]
                        },
                        "users": {
                            "list": [
                                {"id": "11111", "firstName": None, "lastName": None}
                            ]
                        },
                        "pairings": {
                            "list": [
                                {
                                    "id": "00000",
                                    "appId": "00000-00000-00000-00000-00000",
                                    "cid": "00000",
                                    "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                                    "name": "Test Device",
                                    "type": "apw",
                                }
                            ]
                        },
                    },
                    "misc": {},
                    "status": "ok",
                    "errors": [],
                },
            )
        if "command" in url:
            return MockAiohttpResponse(
                200,
                json_data={
                    "ApiVersion": "12",
                    "CommandMode": "parameters",
                    "ParametersData": {
                        "PumpPower": "on",
                        "PumpTemp": "16.000",
                        "PumpMode": "heat",
                        "FanSpeed": "max",
                        "Swing": "off",
                    },
                    "RoomTemp": "27.517",
                    "RoomHumidity": "56",
                },
            )
        return MockAiohttpResponse(404, json_data={})

    mock_session.get.side_effect = _mock_get
    api._access_token = "dummy_token"
    api._user_id = "11111"
    data = await api.get_data()
    assert isinstance(data, list)
    assert len(data) == 1
    unit = data[0]
    assert unit["unit_id"] == "00000"
    assert unit["name"] == "Test Device"
    assert unit["model"] == "AirPatrol APW"


@pytest.mark.asyncio
async def test_get_data_failure(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test data fetch failure due to non-auth error."""

    def _mock_get(url: str, *args: Any, **kwargs: Any) -> MockAiohttpResponse:
        if "pairings" in url:
            return MockAiohttpResponse(500, text_data="Internal Server Error")
        return MockAiohttpResponse(404, json_data={})

    mock_session.get.side_effect = _mock_get
    api._access_token = "dummy_token"
    api._user_id = "197090"
    with pytest.raises(AirPatrolError):
        await api.get_data()


@pytest.mark.asyncio
async def test_get_units(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test getting units from AirPatrol."""

    def _mock_get(url: str, *args: Any, **kwargs: Any) -> MockAiohttpResponse:
        if "pairings" in url:
            return MockAiohttpResponse(
                200,
                json_data={
                    "entities": {
                        "pairingUser": {
                            "list": [
                                {
                                    "userId": "11111",
                                    "pairingId": "00000",
                                    "id": "000011",
                                }
                            ]
                        },
                        "users": {
                            "list": [
                                {"id": "11111", "firstName": None, "lastName": None}
                            ]
                        },
                        "pairings": {
                            "list": [
                                {
                                    "id": "00000",
                                    "appId": "00000-00000-00000-00000-00000",
                                    "cid": "00000",
                                    "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                                    "name": "Test Device",
                                    "type": "apw",
                                }
                            ]
                        },
                    },
                    "misc": {},
                    "status": "ok",
                    "errors": [],
                },
            )
        if "command" in url:
            return MockAiohttpResponse(
                200,
                json_data={
                    "ApiVersion": "12",
                    "CommandMode": "parameters",
                    "ParametersData": {
                        "PumpPower": "on",
                        "PumpTemp": "16.000",
                        "PumpMode": "heat",
                        "FanSpeed": "max",
                        "Swing": "off",
                    },
                    "RoomTemp": "27.517",
                    "RoomHumidity": "56",
                },
            )
        return MockAiohttpResponse(404, json_data={})

    mock_session.get.side_effect = _mock_get
    api._access_token = "dummy_token"
    api._user_id = "11111"
    units = await api.get_units()
    assert isinstance(units, list)
    assert len(units) == 1
    unit = units[0]
    assert unit["unit_id"] == "00000"
    assert unit["name"] == "Test Device"
    assert unit["model"] == "AirPatrol APW"


@pytest.mark.asyncio
async def test_pairings_cache(api: AirPatrolAPI, mock_session: MagicMock) -> None:
    """Test that pairings are cached after first fetch."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "status": "ok",
        "entities": {
            "pairingUser": {
                "list": [
                    {"userId": "test_user_id", "pairingId": "00000", "id": "000011"}
                ]
            },
            "pairings": {
                "list": [
                    {
                        "id": "00000",
                        "appId": "00000-00000-00000-00000-00000",
                        "cid": "00000",
                        "hwid": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                        "name": "Vardagsrum",
                        "type": "apw",
                    }
                ]
            },
        },
        "misc": {},
        "errors": [],
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # First call should fetch from API
    await api.get_pairings()
    mock_session.get.assert_called_once()

    # Second call should use cache
    await api.get_pairings()
    # Should still only be called once (no additional API calls)
    mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_unit_climate_data(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test getting climate data for a unit."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "ApiVersion": "12",
        "CommandMode": "parameters",
        "ParametersData": {
            "PumpPower": "on",
            "PumpTemp": "22.000",
            "PumpMode": "heat",
            "FanSpeed": "max",
            "Swing": "off",
        },
        "RoomTemp": "22.5",
        "RoomHumidity": "45",
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await api.get_unit_climate_data("00000")

    # Verify the correct endpoint and headers were used
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert "https://api.apsrvd.io/12/command" in str(call_args[0][0])
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token"
    assert call_args[1]["headers"]["X-Pairing-Id"] == "00000"

    assert result["RoomTemp"] == "22.5"
    assert result["ParametersData"]["PumpPower"] == "on"


@pytest.mark.asyncio
async def test_set_unit_climate_data(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test setting climate data for a unit."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "ApiVersion": "12",
        "CommandMode": "parameters",
        "ParametersData": {
            "PumpPower": "on",
            "PumpTemp": "25.000",
            "PumpMode": "cool",
            "FanSpeed": "med",
            "Swing": "on",
        },
        "RoomTemp": "24.5",
        "RoomHumidity": "50",
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response

    climate_data = {
        "ApiVersion": "12",
        "CommandMode": "parameters",
        "ParametersData": {
            "PumpPower": "on",
            "PumpTemp": "25.000",
            "PumpMode": "cool",
            "FanSpeed": "med",
            "Swing": "on",
        },
    }

    result = await api.set_unit_climate_data("00000", climate_data)

    # Verify the correct endpoint and headers were used
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert "https://api.apsrvd.io/12/command" in str(call_args[0][0])
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token"
    assert call_args[1]["headers"]["X-Pairing-Id"] == "00000"
    assert call_args[1]["json"] == climate_data

    # Verify the response data is returned
    assert result["RoomTemp"] == "24.5"
    assert result["ParametersData"]["PumpPower"] == "on"


@pytest.mark.asyncio
async def test_set_unit_climate_data_failure(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test set_unit_climate_data returns error."""

    def _mock_post(url: str, *args: Any, **kwargs: Any) -> MockAiohttpResponse:
        return MockAiohttpResponse(400, text_data="Bad Request")

    mock_session.post.side_effect = _mock_post
    api._access_token = "dummy_token"
    api._user_id = "11111"
    with pytest.raises(AirPatrolError):
        await api.set_unit_climate_data("00000", {"foo": "bar"})


@pytest.mark.asyncio
async def test_get_unit_climate_data_failure(
    api: AirPatrolAPI, mock_session: MagicMock
) -> None:
    """Test get_unit_climate_data returns error."""

    def _mock_get(url: str, *args: Any, **kwargs: Any) -> MockAiohttpResponse:
        return MockAiohttpResponse(400, text_data="Bad Request")

    mock_session.get.side_effect = _mock_get
    api._access_token = "dummy_token"
    api._user_id = "11111"
    with pytest.raises(AirPatrolError):
        await api.get_unit_climate_data("00000")
