"""
This module handles API requests.
"""

import aiohttp

from web_app.utils.logger import get_logger

logger = get_logger(__name__)


class APIRequest:
    """
    A class to send asynchronous requests to an API.
    """

    DEFAULT_HEADER = {
        "User-Agent": "Mozilla/5.0",  # Mimic a browser request
        "Accept": "application/json",  # Ensure we expect a JSON response
    }

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def fetch(self, endpoint: str, params: dict = None, headers: dict = None):
        """
        Send a GET request asynchronously with specific headers and query parameters.

        :param endpoint: The API endpoint to send the request to.
        :param params: Query parameters to include in the request.
        :param headers: Headers to include in the request.
        :return: The response from the API as JSON.
        :raises aiohttp.ClientError: On network or HTTP errors.
        """
        # Merge default headers with any user-provided headers
        request_headers = self.DEFAULT_HEADER.copy()  # Start with default headers
        if headers:
            request_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.get(
                url, params=params, headers=request_headers
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def post(self, endpoint: str, data: dict = None, headers: dict = None) -> dict:
        """
        Send a POST request asynchronously.

        :param endpoint: The API endpoint to send the request to.
        :param data: The data to include in the POST request (as a JSON body).
        :param headers: Headers to include in the request.
        :return: The response from the API as JSON.
        :raises aiohttp.ClientError: On network or HTTP errors.
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.post(url, json=data, headers=headers) as response:
                response.raise_for_status()  # Raise an exception for bad status codes
                return await response.json()

    async def fetch_text(
        self, endpoint: str, params: dict = None, headers: dict = None
    ) -> str:
        """
        Send a GET request asynchronously and return text response.

        :param endpoint: The API endpoint to send the request to.
        :param params: Query parameters to include in the request.
        :param headers: Headers to include in the request.
        :return: The response from the API as text.
        :raises aiohttp.ClientError: On network or HTTP errors.
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()  # Raise an exception for bad status codes
                return await response.text()


# Example usage:
async def main():
    """
    Main function to demonstrate APIRequest usage.
    """
    # Initialize the APIRequest with a base URL
    api = APIRequest(base_url="https://portfolio.argent.xyz")

    # Example: Fetch data from an endpoint asynchronously
    response = await api.fetch(
        "/overview/0x020281104e6cb5884dabcdf3be376cf4ff7b680741a7bb20e5e07c26cd4870af"
    )
    logger.info("api_request_example_response", response=response)
