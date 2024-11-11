## Code from https://github.com/litestar-org/litestar/blob/main/litestar/openapi/plugins.py
## and modified to prefix ``spec-url`` with ``settings['FLATMAP_SERVER_URL']``
#===============================================================================
"""
The MIT License (MIT)

Copyright (c) 2021, 2022, 2023, 2024 Litestar Org.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
#===============================================================================

from typing import Any, Sequence

#===============================================================================

from litestar import Request
from litestar.config.csrf import CSRFConfig
from litestar.openapi.plugins import OpenAPIRenderPlugin

#===============================================================================

from ..settings import settings

#===============================================================================

def _get_cookie_value_or_undefined(cookie_name: str) -> str:
    """Javascript code as a string to get the value of a cookie by name or undefined."""
    return f"document.cookie.split('; ').find((row) => row.startsWith('{cookie_name}='))?.split('=')[1];"

#===============================================================================

class RapidocRenderPlugin(OpenAPIRenderPlugin):
    """Render an OpenAPI schema using Rapidoc."""

    def __init__(
        self,
        *,
        version: str = "9.3.4",
        js_url: str | None = None,
        path: str | Sequence[str] = "/rapidoc",
        **kwargs: Any,
    ) -> None:
        """Initialize the OpenAPI UI render plugin.

        Args:
            version: Rapidoc version to download from the CDN. If js_url is provided, this is ignored.
            js_url: Download url for the RapiDoc JS bundle. If not provided, the version will be used to construct the
                url.
            path: Path to serve the OpenAPI UI at.
            **kwargs: Additional arguments to pass to the base class.
        """
        self.js_url = js_url or f"https://unpkg.com/rapidoc@{version}/dist/rapidoc-min.js"
        super().__init__(path=path, **kwargs)

    def render(self, request: Request, openapi_schema: dict[str, Any]) -> bytes:
        """Render an HTML page for Rapidoc.

        .. note:: Override this method to customize the template.

        Args:
            request: The request.
            openapi_schema: The OpenAPI schema as a dictionary.

        Returns:
            A rendered html string.
        """

        def create_request_interceptor(csrf_config: CSRFConfig) -> str:
            if csrf_config.cookie_httponly:
                return ""

            return f"""
            <script>
              window.addEventListener('DOMContentLoaded', (event) => {{
                const rapidocEl = document.getElementsByTagName("rapi-doc")[0];

                rapidocEl.addEventListener('before-try', (e) => {{
                  const csrf_token = {_get_cookie_value_or_undefined(csrf_config.cookie_name)};

                  if (csrf_token !== undefined) {{
                    e.detail.request.headers.append('{csrf_config.header_name}', csrf_token);
                  }}
                }});
              }});
            </script>"""

        head = f"""
          <head>
            <title>{openapi_schema["info"]["title"]}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="{self.js_url}" crossorigin></script>
            {self.style}
          </head>
        """

        body = f"""
          <body>
            <rapi-doc spec-url="{settings['FLATMAP_SERVER_URL']}{self.get_openapi_json_route(request)}" />
            {create_request_interceptor(request.app.csrf_config) if request.app.csrf_config else ""}
          </body>
        """

        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """.encode()

#===============================================================================
#===============================================================================


