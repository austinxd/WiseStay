import logging
import time
from datetime import timedelta

import httpx
from django.conf import settings
from django.utils import timezone

from .exceptions import (
    HostawayAPIError,
    HostawayAuthError,
    HostawayRateLimitError,
)

logger = logging.getLogger(__name__)

# Rate-limit: max 14 requests per 10-second window (leaving margin from 15/10s limit)
_RATE_WINDOW = 10.0
_RATE_MAX_REQUESTS = 14
_REQUEST_TIMEOUT = 30.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds


class HostawayAPIClient:
    """
    HTTP client for the Hostaway REST API.

    Handles OAuth2 token management, rate limiting, and retry with
    exponential backoff.  One instance per usage context (sync engine,
    task, etc.) — it is lightweight and stateless beyond the shared
    credential row.
    """

    def __init__(self):
        self._base_url = settings.HOSTAWAY_API_URL.rstrip("/")
        self._http = httpx.Client(timeout=_REQUEST_TIMEOUT)
        # Simple sliding-window rate limiter
        self._request_timestamps: list[float] = []

    # ------------------------------------------------------------------
    # Public API — Listings
    # ------------------------------------------------------------------

    def get_listings(self, limit: int = 100, offset: int = 0, include_resources: bool = True) -> list:
        params = {"limit": limit, "offset": offset}
        if include_resources:
            params["includeResources"] = 1
        return self._request("GET", "/v1/listings", params=params)

    def get_listing(self, listing_id: int) -> dict:
        return self._request("GET", f"/v1/listings/{listing_id}")

    # ------------------------------------------------------------------
    # Public API — Reservations
    # ------------------------------------------------------------------

    def get_reservations(
        self,
        listing_id: int = None,
        modified_since: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        params = {"limit": limit, "offset": offset}
        if listing_id:
            params["listingId"] = listing_id
        if modified_since:
            params["modifiedSince"] = modified_since
        return self._request("GET", "/v1/reservations", params=params)

    def get_reservation(self, reservation_id: int) -> dict:
        return self._request("GET", f"/v1/reservations/{reservation_id}")

    def create_reservation(self, data: dict) -> dict:
        return self._request("POST", "/v1/reservations", data=data)

    def update_reservation(self, reservation_id: int, data: dict) -> dict:
        return self._request("PUT", f"/v1/reservations/{reservation_id}", data=data)

    # ------------------------------------------------------------------
    # Public API — Calendar
    # ------------------------------------------------------------------

    def get_calendar(self, listing_id: int, start_date: str, end_date: str) -> list:
        params = {"startDate": start_date, "endDate": end_date}
        return self._request("GET", f"/v1/listings/{listing_id}/calendar", params=params)

    # ------------------------------------------------------------------
    # Public API — Conversations / Messages
    # ------------------------------------------------------------------

    def get_conversations(self, reservation_id: int) -> list:
        params = {"reservationId": reservation_id}
        return self._request("GET", "/v1/conversations", params=params)

    def send_message(self, conversation_id: int, body: str) -> dict:
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/messages",
            data={"body": body},
        )

    # ------------------------------------------------------------------
    # Internal — request orchestration
    # ------------------------------------------------------------------

    def _request(self, method: str, endpoint: str, *, params: dict = None, data: dict = None):
        """
        Central request method with auth, rate-limiting, and retry logic.
        Returns the "result" value from the Hostaway response envelope.
        """
        url = f"{self._base_url}{endpoint}" if endpoint.startswith("/v1/") else f"{self._base_url}/v1/{endpoint}"
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            self._throttle()
            t0 = time.monotonic()
            try:
                response = self._http.request(
                    method, url, params=params, json=data, headers=headers,
                )
                elapsed = time.monotonic() - t0
                logger.info(
                    "Hostaway %s %s → %s (%.2fs)",
                    method, endpoint, response.status_code, elapsed,
                )

                # --- Auth error: refresh token once, then retry ----------
                if response.status_code in (401, 403):
                    logger.warning("Hostaway auth error %s on %s — refreshing token", response.status_code, endpoint)
                    if attempt == 1:
                        token = self._refresh_token()
                        headers = {"Authorization": f"Bearer {token}"}
                        continue
                    raise HostawayAuthError(
                        f"Authentication failed for {endpoint}",
                        status_code=response.status_code,
                        response_body=response.text,
                        endpoint=endpoint,
                    )

                # --- Rate limit: backoff and retry -----------------------
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", _BACKOFF_BASE * (2 ** (attempt - 1))))
                    logger.warning(
                        "Hostaway rate limit on %s — waiting %ss (attempt %s/%s)",
                        endpoint, retry_after, attempt, _MAX_RETRIES,
                    )
                    if attempt < _MAX_RETRIES:
                        time.sleep(retry_after)
                        continue
                    raise HostawayRateLimitError(
                        f"Rate limit exceeded for {endpoint}",
                        retry_after=retry_after,
                        status_code=429,
                        response_body=response.text,
                        endpoint=endpoint,
                    )

                # --- Other HTTP errors -----------------------------------
                if response.status_code >= 400:
                    raise HostawayAPIError(
                        f"Hostaway API error {response.status_code} on {endpoint}",
                        status_code=response.status_code,
                        response_body=response.text,
                        endpoint=endpoint,
                    )

                # --- Parse JSON envelope ---------------------------------
                body = response.json()
                if body.get("status") == "fail":
                    raise HostawayAPIError(
                        f"Hostaway API failure: {body.get('result', body.get('message', 'unknown'))}",
                        status_code=response.status_code,
                        response_body=body,
                        endpoint=endpoint,
                    )
                return body.get("result", body)

            except httpx.TimeoutException as exc:
                elapsed = time.monotonic() - t0
                logger.error("Hostaway timeout on %s %s after %.2fs (attempt %s/%s)", method, endpoint, elapsed, attempt, _MAX_RETRIES)
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue

            except httpx.RequestError as exc:
                logger.error("Hostaway connection error on %s %s: %s", method, endpoint, exc)
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue

        raise HostawayAPIError(
            f"Hostaway request failed after {_MAX_RETRIES} attempts on {endpoint}",
            endpoint=endpoint,
        ) from last_exc

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Return a valid access token, fetching a new one if needed."""
        from .models import HostawayCredential
        from common.utils.encryption import decrypt

        cred = HostawayCredential.objects.filter(is_active=True).first()
        if cred is None:
            raise HostawayAuthError("No active Hostaway credential configured")

        if cred.access_token and cred.token_expires_at and cred.token_expires_at > timezone.now():
            try:
                return decrypt(cred.access_token)
            except Exception:
                logger.warning("Failed to decrypt stored token — will refresh")

        return self._refresh_token()

    def _refresh_token(self) -> str:
        """Request a new OAuth2 token from Hostaway and persist it."""
        from .models import HostawayCredential
        from common.utils.encryption import decrypt, encrypt

        cred = HostawayCredential.objects.filter(is_active=True).first()
        if cred is None:
            raise HostawayAuthError("No active Hostaway credential configured")

        try:
            client_secret = decrypt(cred.client_secret)
        except Exception:
            # If the secret isn't encrypted (first-time setup), use as-is
            client_secret = cred.client_secret

        logger.info("Requesting new Hostaway access token for client_id=%s", cred.client_id)

        response = self._http.post(
            f"{self._base_url}/v1/accessTokens",
            data={
                "client_id": cred.client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": "general",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise HostawayAuthError(
                f"Token refresh failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
                endpoint="/v1/accessTokens",
            )

        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise HostawayAuthError(
                "Token refresh response missing access_token",
                response_body=body,
                endpoint="/v1/accessTokens",
            )

        expires_in = int(body.get("expires_in", 86400))
        cred.access_token = encrypt(access_token)
        cred.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        cred.save(update_fields=["access_token", "token_expires_at", "updated_at"])

        logger.info("Hostaway token refreshed, expires at %s", cred.token_expires_at)
        return access_token

    # ------------------------------------------------------------------
    # Rate-limiter (simple sliding window)
    # ------------------------------------------------------------------

    def _throttle(self):
        """Block until we are within the rate-limit window."""
        now = time.monotonic()
        # Purge timestamps older than the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if now - ts < _RATE_WINDOW
        ]
        if len(self._request_timestamps) >= _RATE_MAX_REQUESTS:
            oldest = self._request_timestamps[0]
            sleep_for = _RATE_WINDOW - (now - oldest) + 0.1
            if sleep_for > 0:
                logger.debug("Throttling Hostaway requests for %.2fs", sleep_for)
                time.sleep(sleep_for)
        self._request_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
