
"""Central HTTP client for the FINMARKET FastAPI backend."""

from __future__ import annotations

from typing import Any

import httpx

from streamlit_app.config import API_BASE_URL, REQUEST_TIMEOUT


# ============================================================
# 1. API ERROR
# ============================================================

class APIError(Exception):
    """Raised when the FINMARKET backend API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


# ============================================================
# 2. FINMARKET API CLIENT
# ============================================================

class FinmarketAPI:
    """
    Central HTTP client for FINMARKET FastAPI.

    Supports:
        GET
        POST
        PUT
        PATCH
        DELETE

    Authentication:
        ZITADEL OAuth2 Bearer token.
    """

    def __init__(
        self,
        access_token: str | None = None,
    ) -> None:

        self.base_url = API_BASE_URL.rstrip("/")
        self.access_token = access_token

        self.timeout = REQUEST_TIMEOUT



    def close(self) -> None:
        """Compatibility method for API client cleanup.

        This client uses httpx.request() directly, so it does
        not maintain a persistent HTTP client to close.
        """
        return None


    # ========================================================
    # 3. TOKEN MANAGEMENT
    # ========================================================

    def set_access_token(
        self,
        access_token: str | None,
    ) -> None:

        self.access_token = access_token

    def clear_access_token(self) -> None:

        self.access_token = None

    # ========================================================
    # 4. REQUEST HEADERS
    # ========================================================

    def _headers(self) -> dict[str, str]:

        headers = {
            "Accept": "application/json",
        }

        if self.access_token:

            headers["Authorization"] = (
                f"Bearer {self.access_token}"
            )

        return headers

    # ========================================================
    # 5. RESPONSE PARSING
    # ========================================================

    @staticmethod
    def _parse_response(
        response: httpx.Response,
    ) -> Any:

        if not response.content:
            return None

        try:
            return response.json()

        except ValueError:
            return response.text

    # ========================================================
    # 6. CENTRAL REQUEST METHOD
    # ========================================================

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:

        if not endpoint:
            raise APIError("API endpoint cannot be empty.")

        url = (
            f"{self.base_url}/"
            f"{endpoint.lstrip('/')}"
        )

        try:

            response = httpx.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self.timeout,
                follow_redirects=False,
            )

            response_data = self._parse_response(
                response
            )

            try:

                response.raise_for_status()

            except httpx.HTTPStatusError as exc:

                if isinstance(response_data, dict):

                    detail = (
                        response_data.get("detail")
                        or response_data.get("message")
                        or response_data.get("error")
                        or str(response_data)
                    )

                else:

                    detail = (
                        str(response_data)
                        if response_data
                        else "No additional error information."
                    )

                raise APIError(
                    f"Backend returned HTTP "
                    f"{response.status_code}: {detail}",
                    status_code=response.status_code,
                ) from exc

            return response_data

        except APIError:
            raise

        except httpx.TimeoutException as exc:

            raise APIError(
                f"Request timed out while connecting "
                f"to {self.base_url}."
            ) from exc

        except httpx.RequestError as exc:

            raise APIError(
                f"Cannot connect to FastAPI at "
                f"{self.base_url}. "
                "Check whether the backend server is running."
            ) from exc

    # ========================================================
    # 7. GET REQUEST
    # ========================================================

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:

        return self.request(
            "GET",
            endpoint,
            params=params,
        )

    # ========================================================
    # 8. POST REQUEST
    # ========================================================

    def post(
        self,
        endpoint: str,
        payload: Any = None,
    ) -> Any:

        return self.request(
            "POST",
            endpoint,
            json=payload,
        )

    # ========================================================
    # 9. PUT REQUEST
    # ========================================================

    def put(
        self,
        endpoint: str,
        payload: Any = None,
    ) -> Any:

        return self.request(
            "PUT",
            endpoint,
            json=payload,
        )

    # ========================================================
    # 10. PATCH REQUEST
    # ========================================================

    def patch(
        self,
        endpoint: str,
        payload: Any = None,
    ) -> Any:

        return self.request(
            "PATCH",
            endpoint,
            json=payload,
        )

    # ========================================================
    # 11. DELETE REQUEST
    # ========================================================

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:

        return self.request(
            "DELETE",
            endpoint,
            params=params,
        )
