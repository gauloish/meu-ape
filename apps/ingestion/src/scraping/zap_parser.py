"""ZAP Imóveis property listing parser module.

Provides a unified parsing interface to convert raw JSON-LD structured data items
retrieved from Zap Imóveis web pages into normalised dictionary records, along with
canonical URL normalisation, ID extraction from URLs, and HTML structure analysis.
"""

import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup


def normalize_url(url: str | None) -> str | None:
    """Normalise a listing URL to its canonical form without query or fragment.

    Args:
        url: Raw listing URL string.

    Returns:
        Canonical URL string with lowercase scheme/host and trailing slash,
        or None if empty/invalid.
    """
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    if not cleaned:
        return None

    parts = urlsplit(cleaned)
    if not parts.scheme or not parts.netloc:
        return cleaned

    path = re.sub(r"/+", "/", parts.path or "/")
    if not path.endswith("/"):
        path = f"{path}/"

    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def extract_id_from_url(url: str | None) -> str | None:
    """Extract the canonical listing ID from a Zap Imóveis listing URL.

    Supports both slugged URLs ending in ``-id-<digits>/`` and direct
    ``/imovel/<digits>/`` paths.

    Args:
        url: Listing URL string.

    Returns:
        Extracted identifier string if matched, otherwise None.
    """
    if not url or not isinstance(url, str):
        return None

    slug_match = re.search(r"-id-(\d+)(?:/|$|\?)", url, re.IGNORECASE)
    if slug_match:
        return slug_match.group(1)

    direct_match = re.search(r"/imovel/(\d+)(?:/|$|\?)", url, re.IGNORECASE)
    if direct_match:
        return direct_match.group(1)

    return None


def _extract_parking_spots(title: str) -> int | None:
    """Extract the count of parking spots from a listing title.

    Args:
        title: Raw title string from the property listing.

    Returns:
        Number of parking spots if matched, otherwise None.
    """
    match = re.search(r"(\d+)\s+vagas?", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_neighbourhood(title: str) -> str | None:
    """Extract the neighbourhood name from a listing title.

    Args:
        title: Raw title string from the property listing.

    Returns:
        Neighbourhood string if matched, otherwise None.
    """
    match = re.search(r"em\s+(.+?),\s*(?:Goiânia|GO|Brasil)", title, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_property_type(item: dict[str, Any], title: str) -> str | None:
    """Derive property type from additionalType or listing title.

    Args:
        item: Raw item dictionary from JSON-LD schema.
        title: Raw title string from the property listing.

    Returns:
        Extracted property type string or None.
    """
    add_type = item.get("additionalType", "")
    if "/" in str(add_type):
        return add_type.split("/")[-1]
    return title.split()[0] if title else None


def _join_photo_urls(images: Any) -> str:
    """Format image URL attributes into a comma-separated string."""
    if isinstance(images, list):
        return ", ".join(images)
    return str(images) if images else ""


def _extract_condo_fee(offers: dict[str, Any]) -> float | None:
    """Extract condominium fee from additional properties dict."""
    add_prop = offers.get("additionalProperty", {})
    if isinstance(add_prop, dict) and add_prop.get("name") == "Condominium Fee":
        return add_prop.get("value")
    return None


def inspect_html_structure(html: str) -> dict[str, Any]:
    """Inspect public HTML and return structured diagnostics about JSON-LD and WAF blocks.

    Args:
        html: Raw HTML response body.

    Returns:
        Dictionary with detected JSON-LD schema types, item count, H1 total count,
        and whether the HTML represents an edge WAF challenge/block page.
    """
    if not html:
        return {
            "json_ld_types": [],
            "item_list_count": 0,
            "h1_total_count": None,
            "is_waf_challenge": False,
        }

    soup = BeautifulSoup(html, "html.parser")
    json_ld_types: list[str] = []
    item_list_count = 0

    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
            if isinstance(payload, dict):
                schema_type = payload.get("@type")
                if schema_type:
                    json_ld_types.append(str(schema_type))
                if schema_type == "ItemList":
                    elements = payload.get("itemListElement", [])
                    if isinstance(elements, list):
                        item_list_count += len(elements)
        except Exception:  # noqa: BLE001, S110
            pass

    h1_total_count: int | None = None
    h1 = soup.find("h1")
    if h1 and h1.text:
        match = re.search(r"([\d\.]+)", h1.text)
        if match:
            try:
                h1_total_count = int(match.group(1).replace(".", ""))
            except ValueError:
                h1_total_count = None

    lower_html = html.lower()
    is_waf_challenge = any(
        marker in lower_html
        for marker in (
            "cf-browser-verification",
            "challenge-platform",
            "just a moment...",
            "attention required! | cloudflare",
            "access denied",
        )
    )

    return {
        "json_ld_types": json_ld_types,
        "item_list_count": item_list_count,
        "h1_total_count": h1_total_count,
        "is_waf_challenge": is_waf_challenge,
    }


def parse_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw JSON-LD listing object into a tabular dictionary.

    Args:
        item: Dictionary corresponding to an ItemList entry from Zap Imóveis
            structured HTML data.

    Returns:
        A dictionary containing normalised property fields ready for DataFrame
        export or CSV persistence.
    """
    offers: dict[str, Any] = (
        item.get("offers", {}) if isinstance(item.get("offers"), dict) else {}
    )
    address: dict[str, Any] = (
        item.get("address", {}) if isinstance(item.get("address"), dict) else {}
    )
    floor_size: dict[str, Any] = (
        item.get("floorSize", {}) if isinstance(item.get("floorSize"), dict) else {}
    )

    title: str = item.get("name", "") or ""
    raw_url = item.get("url")
    canonical_url = normalize_url(raw_url) if raw_url else None
    listing_id = (
        item.get("@id")
        or item.get("id")
        or extract_id_from_url(canonical_url or raw_url)
    )

    amenities = [
        af["value"]
        for af in item.get("amenityFeature", [])
        if isinstance(af, dict) and af.get("value")
    ]

    return {
        "id": str(listing_id) if listing_id is not None else None,
        "titulo": title,
        "tipo_imovel": _extract_property_type(item, title),
        "url": canonical_url,
        "preco": offers.get("price"),
        "moeda": offers.get("priceCurrency", "BRL"),
        "condominio": _extract_condo_fee(offers),
        "area_m2": floor_size.get("value"),
        "quartos": item.get("numberOfBedrooms") or item.get("numberOfRooms"),
        "banheiros": item.get("numberOfBathroomsTotal"),
        "vagas": _extract_parking_spots(title),
        "bairro": _extract_neighbourhood(title),
        "rua": address.get("streetAddress"),
        "cidade": address.get("addressLocality"),
        "estado": address.get("addressRegion"),
        "pais": address.get("addressCountry"),
        "aceita_pets": item.get("petsAllowed"),
        "comodidades": ", ".join(amenities),
        "fotos_urls": _join_photo_urls(item.get("image", [])),
        "descricao_completa": item.get("description"),
        "data_publicacao": item.get("datePublished"),
        "data_modificacao": item.get("dateModified"),
        "scraped_at": datetime.now(UTC).isoformat(),
    }
