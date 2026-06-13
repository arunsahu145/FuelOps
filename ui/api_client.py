"""
Petrol Pump Finance Manager ERP — API HTTP Client Wrapper
Handles connection to the in-process FastAPI server.
"""
import httpx
from typing import Optional, Any, Dict
from config import API_BASE_URL


class APIClient:
    _instance: Optional["APIClient"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(APIClient, cls).__new__(cls, *args, **kwargs)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        self.base_url = API_BASE_URL
        self.token: Optional[str] = None
        self.client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def set_token(self, token: str):
        self.token = token
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    def clear_token(self):
        self.token = None
        if "Authorization" in self.client.headers:
            del self.client.headers["Authorization"]

    def is_authenticated(self) -> bool:
        return self.token is not None

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user and store token."""
        response = self.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            self.set_token(data["access_token"])
            return {"success": True, "data": data}
        else:
            try:
                err_detail = response.json().get("detail", "Authentication failed")
            except Exception:
                err_detail = "Failed to reach server"
            return {"success": False, "error": err_detail}

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a GET request."""
        response = self.client.get(endpoint, params=params)
        return self._handle_response(response)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a POST request."""
        response = self.client.post(endpoint, json=data)
        return self._handle_response(response)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a PUT request."""
        response = self.client.put(endpoint, json=data)
        return self._handle_response(response)

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a DELETE request."""
        response = self.client.delete(endpoint, params=params)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code in [200, 201]:
            return response.json()
        else:
            try:
                detail = response.json().get("detail", "API Error")
            except Exception:
                detail = f"HTTP Error {response.status_code}"
            raise Exception(detail)


# Create a global instance
client = APIClient()
