"""Shopify Admin GraphQL — auth + transport, nothing else.

credentials resolve from the macOS Keychain by service name, in-process,
at call time; the 24h client-credentials token is cached in memory only,
never on disk. instance config (shop domain, keychain service names) is
stores/<store>/connector.json — names and references only, never secrets.
every failure raises (fail closed): a call that errored is never handed
back as data. transport is stdlib urllib — zero new runtime deps for A3;
the pattern is mined from the tombstoned v0, rewritten clean.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from commerceos import stores


class CredentialsUnavailable(RuntimeError):
    """the Keychain has no entry under the configured service name."""


class ShopifyError(RuntimeError):
    """auth, transport, or GraphQL failure — the call did not succeed."""


def load_config(path: Path | str | None = None) -> dict:
    """read the instance config (shop domain, keychain service names)."""
    p = Path(path) if path else stores.resolve(stores.active_store(), "connector.json")
    with open(p) as f:
        return json.load(f)


def keychain_secret(service: str) -> str:
    """resolve one secret from the macOS Keychain, in-process.

    the value stays inside this process — never logged, never written.
    """
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CredentialsUnavailable(f"keychain probe failed for {service}: {e}") from e
    if out.returncode != 0:
        raise CredentialsUnavailable(
            f"keychain entry not found: {service}"
            f" (store it: security add-generic-password -s {service} -w ...)"
        )
    return out.stdout.strip()


def credentials_available(config: dict | None = None) -> bool:
    """probe only — True when the client secret resolves. never returns the value."""
    try:
        config = config or load_config()
        keychain_secret(config["keychain"]["client_secret"])
    except (CredentialsUnavailable, OSError, KeyError, ValueError):
        return False
    return True


class ShopifyClient:
    """one shop, one token cached in memory, one graphql() that raises on error."""

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.shop = self.config["shop_domain"]
        self.api_version = self.config.get("api_version", "2026-04")
        self._token: str | None = None
        self._token_exp = 0.0

    @property
    def graphql_url(self) -> str:
        return f"https://{self.shop}/admin/api/{self.api_version}/graphql.json"

    def _access_token(self) -> str:
        """client-credentials grant -> 24h token, cached in memory, refreshed early."""
        now = time.time()
        if self._token and now < self._token_exp - 60:
            return self._token
        services = self.config["keychain"]
        try:
            client_id = keychain_secret(services["client_id"])
        except CredentialsUnavailable:
            client_id = self.config.get("client_id")  # public OAuth id from config, not a secret
            if not client_id:
                raise
        client_secret = keychain_secret(services["client_secret"])
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        ).encode()
        req = urllib.request.Request(
            f"https://{self.shop}/admin/oauth/access_token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            raise ShopifyError(
                f"token exchange failed: HTTP {e.code} (check the Keychain secret) {detail}"
            ) from e
        except OSError as e:  # URLError, timeouts, connection resets
            raise ShopifyError(f"token exchange failed: {e}") from e
        self._token = d["access_token"]
        self._token_exp = now + int(d.get("expires_in", 86_399))
        return self._token

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        """one Admin GraphQL call -> the data dict. any error raises (fail closed)."""
        token = self._access_token()
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(
            self.graphql_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": token,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise ShopifyError(
                f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
            ) from e
        except OSError as e:
            raise ShopifyError(f"network error: {e}") from e
        if d.get("errors"):
            raise ShopifyError(f"graphql errors: {json.dumps(d['errors'])[:500]}")
        return d.get("data") or {}
