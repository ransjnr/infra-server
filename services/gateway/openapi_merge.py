"""Merge upstream OpenAPI specs into the gateway schema (single Swagger UI)."""

from __future__ import annotations

import copy
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BEARER_SECURITY: list[dict[str, list[str]]] = [{"BearerAuth": []}]


def _rewrite_schema_refs(obj: Any, prefix: str) -> None:
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", maxsplit=1)[-1]
            obj["$ref"] = f"#/components/schemas/{prefix}{name}"
        for v in obj.values():
            _rewrite_schema_refs(v, prefix)
    elif isinstance(obj, list):
        for item in obj:
            _rewrite_schema_refs(item, prefix)


def _prefix_components(doc: dict[str, Any], prefix: str) -> dict[str, Any]:
    comps = doc.get("components") or {}
    schemas = comps.get("schemas") or {}
    out: dict[str, Any] = {}
    for name, schema in schemas.items():
        out[f"{prefix}{name}"] = copy.deepcopy(schema)
    return out


def _skip_upstream_path(path_key: str) -> bool:
    """Omit docs/redoc/openapi and service root hello from merged catalog."""
    if path_key in ("/docs", "/redoc", "/openapi.json"):
        return True
    if path_key in ("/", ""):
        return True
    return False


def _transform_paths(
    doc: dict[str, Any],
    *,
    api_prefix: str,
    schema_prefix: str,
    apply_bearer_security: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths_in = doc.get("paths") or {}
    new_paths: dict[str, Any] = {}
    for path_key, path_item in paths_in.items():
        if _skip_upstream_path(path_key):
            continue
        new_key = f"{api_prefix}{path_key}" if path_key.startswith("/") else f"{api_prefix}/{path_key}"
        if not new_key.startswith("/"):
            new_key = "/" + new_key
        cloned = copy.deepcopy(path_item)
        _rewrite_schema_refs(cloned, schema_prefix)
        for _method, op in cloned.items():
            if not isinstance(op, dict):
                continue
            if _method.lower() in frozenset(
                {"get", "post", "put", "patch", "delete", "head", "options"}
            ):
                if apply_bearer_security and op.get("security") is None:
                    op["security"] = copy.deepcopy(_BEARER_SECURITY)
                op.setdefault("tags", [])
                if isinstance(op["tags"], list):
                    op["tags"] = [f"{t} (proxied)" for t in op["tags"]]
        new_paths[new_key] = cloned
    return new_paths, _prefix_components(doc, schema_prefix)


def merge_upstream_into_schema(
    base: dict[str, Any],
    *,
    client: httpx.Client,
    base_url: str,
    api_prefix: str,
    schema_prefix: str,
    apply_bearer_security: bool = True,
) -> None:
    """Fetch ``/openapi.json`` from an upstream and merge paths + schemas into ``base``."""
    url = f"{base_url.rstrip('/')}/openapi.json"
    try:
        r = client.get(url, timeout=15.0)
        r.raise_for_status()
        doc = r.json()
    except Exception as exc:
        logger.warning("Could not merge OpenAPI from %s: %s", url, exc)
        return

    paths, prefixed_schemas = _transform_paths(
        doc,
        api_prefix=api_prefix,
        schema_prefix=schema_prefix,
        apply_bearer_security=apply_bearer_security,
    )
    base.setdefault("paths", {}).update(paths)
    base.setdefault("components", {}).setdefault("schemas", {}).update(prefixed_schemas)


def ensure_bearer_security_scheme(schema: dict[str, Any]) -> None:
    comps = schema.setdefault("components", {})
    schemes = comps.setdefault("securitySchemes", {})
    schemes.setdefault(
        "BearerAuth",
        {"type": "http", "scheme": "bearer", "bearerFormat": "JWT", "description": "JWT from POST /auth/login"},
    )
