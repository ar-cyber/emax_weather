"""API client for Emax Weather Station."""

import asyncio
import hashlib
import json
import logging
from typing import Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class EmaxWeatherAPIClient:
    """Client for Emax Weather Station API."""

    def __init__(
        self,
        email: str,
        password: str,
        base_url: str = "https://app.emaxlife.net/V1.0",
        timeout: int = 10,
    ):
        """Initialize API client."""
        self.email = email
        self.password = password
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.token: Optional[str] = None
        self.user_data: Optional[dict] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)  # Like app's TrustAllManager
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )
        return self._session

    async def _hash_password(self) -> str:
        """Hash password with salt."""
        salt = "emax@pwd123"
        password_with_salt = f"{self.password}{salt}"
        return hashlib.md5(password_with_salt.encode()).hexdigest()

    async def async_login(self) -> bool:
        """Login and get authentication token."""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/account/login"

            pwd_hash = await self._hash_password()

            payload = {
                "email": self.email,
                "pwd": pwd_hash,
            }

            _LOGGER.debug(f"Logging in as {self.email}")

            async with session.post(url, json=payload) as resp:
                _LOGGER.debug(f"Login response json: {await resp.json()}")

                data = await resp.json()



                content = data.get("content")
                if not content or "token" not in content:
                    _LOGGER.error("No token in login response")
                    return False

                self.token = content["token"]
                self.user_data = content

                _LOGGER.info(
                    f"Successfully logged in as {content.get('nickname', self.email)}"
                )
                return True

        except asyncio.TimeoutError:
            _LOGGER.error("Login timeout")
            return False
        except Exception as err:
            _LOGGER.error(f"Login error: {err}")
            return False

    async def async_get_realtime_weather(self) -> Optional[dict]:
        """Get realtime weather data."""
        try:
            if not self.token:
                if not await self.async_login():
                    return None

            session = await self._get_session()
            url = f"{self.base_url}/weather/devData/getRealtime"

            headers = {
                "emaxToken": self.token,
                "User-Agent": "Emax-Weather-App/3.0 Android/10",
            }

            _LOGGER.debug("Fetching realtime weather data")

            async with session.get(url, headers=headers) as resp:


                data = await resp.json()


                content = data.get("content")
                if not content:
                    _LOGGER.error("No content in weather response")
                    return None

                _LOGGER.debug("Successfully retrieved weather data")
                return content

        except asyncio.TimeoutError:
            _LOGGER.error("Weather request timeout")
            return None
        except Exception as err:
            _LOGGER.error(f"Weather request error: {err}")
            return None

    async def async_get_weather_history(
        self,
        start_date: str,
        end_date: str,
    ) -> Optional[dict]:
        """Get historical weather data."""
        try:
            if not self.token:
                if not await self.async_login():
                    return None

            session = await self._get_session()
            url = f"{self.base_url}/weather/devData/getRecord"

            headers = {
                "emaxToken": self.token
            }

            params = {
                "startDate": start_date,
                "endDate": end_date,
            }

            _LOGGER.debug(f"Fetching weather history from {start_date} to {end_date}")

            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"History request failed with status {resp.status}")
                    return None

                data = await resp.json()

                if data.get("status") != "0":
                    error_msg = data.get("message", "Unknown error")
                    _LOGGER.error(f"History request failed: {error_msg}")
                    return None

                return data.get("content")

        except Exception as err:
            _LOGGER.error(f"History request error: {err}")
            return None

    async def async_get_binded_devices(self) -> Optional[list]:
        """Get list of binded devices."""
        try:
            if not self.token:
                if not await self.async_login():
                    return None

            session = await self._get_session()
            url = f"{self.base_url}/weather/getBindedDevice"

            headers = {
                "emaxToken": self.token,
                "User-Agent": "Emax-Weather-App/3.0 Android/10",
            }

            _LOGGER.debug("Fetching binded devices")

            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.error(f"Devices request failed with status {resp.status}")
                    return None

                data = await resp.json()

                if data.get("status") != "0":
                    error_msg = data.get("message", "Unknown error")
                    _LOGGER.error(f"Devices request failed: {error_msg}")
                    return None

                return data.get("content", [])

        except Exception as err:
            _LOGGER.error(f"Devices request error: {err}")
            return None

    async def async_close(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
