"""Thin async client for the OvenMediaEngine REST API v1."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class OmeApiError(Exception):
    """Generic OME API error."""


class OmeAuthError(OmeApiError):
    """Authentication failed (HTTP 401)."""


class OmeConnectionError(OmeApiError):
    """The server could not be reached."""


def normalize_base_url(base_url: str) -> str:
    """Normalise a user-supplied base URL.

    Accepts values like ``restreamer.example.com/api``,
    ``https://restreamer.example.com/api`` or ``http://192.168.1.10:8081``.
    A missing scheme defaults to ``http://``; trailing slashes are stripped.
    """
    url = base_url.strip().rstrip("/")
    if "://" not in url:
        url = f"http://{url}"
    return url


class OmeApiClient:
    """Minimal read-only client for OvenMediaEngine stats."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        access_token: str,
        verify_ssl: bool = True,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._base_url = f"{normalize_base_url(base_url)}/v1"
        # OME expects the *entire* access token base64-encoded as Basic auth.
        # The token itself may contain a ':' which must NOT be treated as a
        # user/password separator, so we encode the raw string ourselves.
        token = base64.b64encode(access_token.encode()).decode()
        self._headers = {"Authorization": f"Basic {token}"}
        self._verify_ssl = verify_ssl

    async def _get(self, path: str) -> Any:
        """GET ``path`` (relative to /v1) and return the unwrapped response.

        Raises ``OmeAuthError`` on 401, ``OmeApiError`` on other non-2xx,
        and ``OmeConnectionError`` on transport problems.
        """
        url = f"{self._base_url}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.get(
                    url, headers=self._headers, ssl=self._verify_ssl
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            # ValueError covers aiohttp.InvalidURL for malformed base URLs.
            raise OmeConnectionError(f"Error connecting to {url}: {err}") from err

        if resp.status == 401:
            raise OmeAuthError("Invalid access token")
        if resp.status == 404:
            raise OmeApiError(f"Not found: {path}")
        if resp.status >= 400:
            raise OmeApiError(f"Unexpected status {resp.status} for {path}")

        try:
            payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as err:
            # Non-JSON body (e.g. a reverse proxy serving HTML at this URL).
            raise OmeConnectionError(
                f"Response from {url} is not valid JSON — is the base URL "
                f"pointing at the OME REST API?"
            ) from err
        # Responses are wrapped as {statusCode, message, response}.
        if isinstance(payload, dict) and "response" in payload:
            return payload["response"]
        return payload

    async def async_get_vhosts(self) -> list[str]:
        """Return the list of virtual host names."""
        return list(await self._get("/vhosts") or [])

    async def async_get_apps(self, vhost: str) -> list[str]:
        """Return the list of application names for a vhost."""
        return list(await self._get(f"/vhosts/{vhost}/apps") or [])

    async def async_get_streams(self, vhost: str, app: str) -> list[str]:
        """Return the list of stream names for an app."""
        return list(await self._get(f"/vhosts/{vhost}/apps/{app}/streams") or [])

    async def async_get_vhost_stats(self, vhost: str) -> dict[str, Any]:
        """Return Metrics for a vhost."""
        return await self._get(f"/stats/current/vhosts/{vhost}") or {}

    async def async_get_app_stats(self, vhost: str, app: str) -> dict[str, Any]:
        """Return Metrics for an app."""
        return await self._get(f"/stats/current/vhosts/{vhost}/apps/{app}") or {}

    async def async_get_stream_stats(
        self, vhost: str, app: str, stream: str
    ) -> dict[str, Any]:
        """Return Metrics for a stream."""
        return (
            await self._get(
                f"/stats/current/vhosts/{vhost}/apps/{app}/streams/{stream}"
            )
            or {}
        )

    async def async_validate(self) -> None:
        """Lightweight connectivity/auth check used by the config flow."""
        await self.async_get_vhosts()

    async def async_fetch_all(self) -> dict[str, Any]:
        """Walk vhosts -> apps -> streams and collect stats for every object.

        Returns a nested structure::

            {vhost: {"stats": Metrics,
                     "apps": {app: {"stats": Metrics,
                                    "streams": {stream: Metrics}}}}}

        Objects that disappear mid-walk (404) are skipped rather than failing
        the whole refresh.
        """
        result: dict[str, Any] = {}
        for vhost in await self.async_get_vhosts():
            try:
                vhost_stats = await self.async_get_vhost_stats(vhost)
            except OmeApiError:
                vhost_stats = {}
            apps: dict[str, Any] = {}
            try:
                app_names = await self.async_get_apps(vhost)
            except OmeApiError:
                app_names = []
            for app in app_names:
                try:
                    app_stats = await self.async_get_app_stats(vhost, app)
                except OmeApiError:
                    app_stats = {}
                streams: dict[str, Any] = {}
                try:
                    stream_names = await self.async_get_streams(vhost, app)
                except OmeApiError:
                    stream_names = []
                for stream in stream_names:
                    try:
                        streams[stream] = await self.async_get_stream_stats(
                            vhost, app, stream
                        )
                    except OmeApiError:
                        # Stream vanished between listing and stats fetch.
                        continue
                apps[app] = {"stats": app_stats, "streams": streams}
            result[vhost] = {"stats": vhost_stats, "apps": apps}
        return result
