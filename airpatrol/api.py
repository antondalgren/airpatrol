"""AirPatrol API client."""

from __future__ import annotations

import logging
from typing import Any, Dict, cast

from aiohttp import ClientSession

from .const import (
    API_BASE_URL,
    API_COMMAND_ENDPOINT,
    AUTH_BASE_URL,
    AUTH_LOGIN_ENDPOINT,
    AUTH_PAIRINGS_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class AirPatrolAuthenticationError(Exception):
    """Exception raised when authentication fails."""


class AirPatrolError(Exception):
    """Exception raised when an unexpected error occurs."""


class AirPatrolAPI:
    """AirPatrol API client."""

    def __init__(
        self, session: ClientSession, access_token: str, user_id: str | None = None
    ) -> None:
        """Initialize."""
        self._session = session
        self._access_token = access_token
        self._user_id = user_id
        self._pairings_cache: dict[str, Any] | None = None

    @staticmethod
    async def authenticate(
        session: ClientSession, email: str, password: str
    ) -> AirPatrolAPI:
        """Test if we can authenticate with the host.

        Returns
        -------
        AirPatrolAPI instance if authentication is successful

        """
        async with session.post(
            f"{AUTH_BASE_URL}{AUTH_LOGIN_ENDPOINT}",
            json={"email": email, "password": password},
        ) as resp:
            _LOGGER.debug("Authenticating with %s", resp.url)
            if resp.status != 200:
                _LOGGER.error("Authentication failed with status %s", resp.status)
                _LOGGER.error("Response: %s", await resp.text())
                raise AirPatrolAuthenticationError("Authentication failed")

            data = await resp.json()
            if data.get("status") == "ok":
                user_id = data["entities"]["users"]["list"][0]["id"]
                access_token = data["misc"]["accessToken"]
                return AirPatrolAPI(session, access_token, user_id)
        raise AirPatrolAuthenticationError("Authentication failed")

    def get_unique_id(self) -> str:
        """Get unique ID for the user."""
        if self._user_id is None:
            raise ValueError("Not authenticated")
        return self._user_id

    def get_access_token(self) -> str | None:
        """Get the access token."""
        return self._access_token

    def clear_pairings_cache(self) -> None:
        """Clear the pairings cache to force a fresh fetch."""
        self._pairings_cache = None

    async def get_pairings(self) -> dict[str, Any]:
        """Get pairings (devices) from AirPatrol API."""
        # Return cached data if available
        if self._pairings_cache is not None:
            _LOGGER.debug("Returning cached pairings data")
            return self._pairings_cache

        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with self._session.get(
            f"{AUTH_BASE_URL}{AUTH_PAIRINGS_ENDPOINT}",
            headers=headers,
        ) as resp:
            _LOGGER.debug("Fetching pairings from %s", resp.url)
            if resp.status in [401, 403]:
                _LOGGER.error("Authentication failed with status %s", resp.status)
                _LOGGER.error("Response: %s", await resp.text())
                raise AirPatrolAuthenticationError("Failed to fetch pairings")

            if resp.status == 200:
                data = cast(Dict[str, Any], await resp.json())
                if data.get("status") != "ok":
                    _LOGGER.error("API returned error status: %s", data.get("errors"))
                    raise AirPatrolError("API returned error status")

                # Cache the successful response
                self._pairings_cache = data
                _LOGGER.debug("Cached pairings data")
                return data

        raise AirPatrolError(f"Failed to fetch pairings: {resp.status}")

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices (pairings) for the authenticated user."""
        data = await self.get_pairings()

        # Get the user's pairings
        user_pairings = []
        pairing_users = data.get("entities", {}).get("pairingUser", {}).get("list", [])

        for pairing_user in pairing_users:
            if pairing_user.get("userId") == self._user_id:
                pairing_id = pairing_user.get("pairingId")
                # Find the corresponding pairing details
                pairings = data.get("entities", {}).get("pairings", {}).get("list", [])
                for pairing in pairings:
                    if pairing.get("id") == pairing_id:
                        user_pairings.append(pairing)
                        break

        return user_pairings

    async def get_data(self) -> list[dict[str, Any]]:
        """Get data from AirPatrol."""
        devices = await self.get_devices()
        units = []
        for device in devices:
            unit_id = device.get("id")
            if not isinstance(unit_id, str):
                continue  # Skip if unit_id is not a string
            # Get climate data for this unit
            climate_data = await self.get_unit_climate_data(unit_id)

            unit_data = {
                "unit_id": unit_id,
                "name": device.get("name", f"AirPatrol Device {unit_id}"),
                "model": f"AirPatrol {device.get('type', 'Unknown').upper()}",
                "manufacturer": "AirPatrol",
                "hwid": device.get("hwid"),
                "type": device.get("type"),
                "app_id": device.get("appId"),
                # Climate data
                "climate": climate_data,
            }
            units.append(unit_data)
        return units

    async def get_units(self) -> list[dict[str, Any]]:
        """Get list of units from AirPatrol."""
        return await self.get_data()

    async def get_unit_climate_data(self, unit_id: str) -> dict[str, Any]:
        """Get climate data for a specific unit."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-Pairing-Id": unit_id,
        }
        async with self._session.get(
            f"{API_BASE_URL}{API_COMMAND_ENDPOINT}",
            headers=headers,
        ) as resp:
            _LOGGER.debug(
                "Fetching climate data for unit %s from %s", unit_id, resp.url
            )
            if resp.status in [401, 403]:
                _LOGGER.error(
                    "Failed to fetch climate data for unit %s with status %s",
                    unit_id,
                    resp.status,
                )
                raise AirPatrolAuthenticationError("Failed to fetch climate data")

            if resp.status == 200:
                return cast(Dict[str, Any], await resp.json())

        raise AirPatrolError(f"Failed to fetch climate data: {resp.status}")

    async def set_unit_climate_data(
        self, unit_id: str, climate_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Set climate data for a specific unit."""
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-Pairing-Id": unit_id,
        }
        async with self._session.post(
            f"{API_BASE_URL}{API_COMMAND_ENDPOINT}",
            headers=headers,
            json=climate_data,
        ) as resp:
            _LOGGER.debug("Setting climate data for unit %s", unit_id)
            if resp.status in [401, 403]:
                _LOGGER.error(
                    "Failed to set climate data for unit %s with status %s",
                    unit_id,
                    resp.status,
                )
                raise AirPatrolAuthenticationError("Failed to set climate data")

            if resp.status == 200:
                return cast(Dict[str, Any], await resp.json())

        raise AirPatrolError(f"Failed to set climate data: {resp.status}")
