"""
Redfish client wrapper for HPE Redfish Exporter
"""

from redfish import redfish_client # type: ignore
from typing import Optional, List, Any
import urllib3


class RedfishClientWrapper:
    """Wrapper for Redfish client with safe operations"""

    def __init__(
        self, urls: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 10
    ):
        self.urls = urls
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client: Optional[Any] = None

    def connect(self) -> bool:
        """Establish connection to Redfish API"""
        for url in self.urls:
            try:
                # Disable warnings for self-signed certificates
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                print(f"INFO: trying to connect to {url}")

                self.client = redfish_client(
                    base_url=url,
                    username=self.username,
                    password=self.password,
                    default_prefix="/redfish/v1",
                    check_connectivity=True,
                    timeout=self.timeout,
                )
                self.client.login(auth="session")
            except Exception as e:
                print(f"ERROR: Failed to connect to Redfish API: {e}")
                continue
            else:
                return True
        else:
            print(f"ERROR: Unable to connect to any host!")
            return False


    def safe_get(self, path: str) -> Optional[Any]:
        """Safely get resource from Redfish API"""
        try:
            if not self.client:
                return None
            return self.client.get(path)
        except Exception:
            return None

    def logout(self):
        """Logout from Redfish API"""
        try:
            if self.client:
                self.client.logout()
        except Exception:
            pass
