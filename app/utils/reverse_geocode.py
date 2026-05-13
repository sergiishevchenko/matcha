"""Resolve city / neighborhood label from coordinates (OpenStreetMap Nominatim via geopy).

Nominatim usage policy: low volume only; https://operations.osmfoundation.org/policies/nominatim/
"""

from __future__ import annotations

from typing import Any, Optional

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

_USER_AGENT = "MatchaSchoolProject/1.0 (contact: local dev)"
_MAX_LEN = 200

_geolocator: Optional[Nominatim] = None


def _get_geolocator() -> Nominatim:
    global _geolocator
    if _geolocator is None:
        _geolocator = Nominatim(user_agent=_USER_AGENT, timeout=12)
    return _geolocator


def build_place_label_from_address(address: dict[str, Any], display_name: str | None) -> str | None:
    """Build a short human label (neighborhood, district, city) from Nominatim address parts."""
    if not address:
        if display_name:
            parts = [p.strip() for p in display_name.split(",") if p.strip()]
            return ", ".join(parts[:3])[:_MAX_LEN] if parts else None
        return None
    bits: list[str] = []
    for key in ("neighbourhood", "suburb", "quarter", "city_district", "district", "hamlet"):
        v = address.get(key)
        if v and str(v).strip() and str(v).strip() not in bits:
            bits.append(str(v).strip())
    for key in ("city", "town", "village", "municipality"):
        v = address.get(key)
        if v and str(v).strip() and str(v).strip() not in bits:
            bits.append(str(v).strip())
            break
    if bits:
        return ", ".join(bits)[:_MAX_LEN]
    if display_name:
        parts = [p.strip() for p in display_name.split(",") if p.strip()]
        return ", ".join(parts[:3])[:_MAX_LEN] if parts else None
    return None


def reverse_geocode_neighborhood(lat: float, lng: float) -> str | None:
    """
    Reverse-geocode (lat, lng) to a neighborhood / city string for location_place.
    Returns None on failure or empty result.
    """
    try:
        loc = _get_geolocator().reverse((lat, lng), zoom=18, language="en")
    except (GeocoderTimedOut, GeocoderServiceError, OSError, ValueError):
        return None
    if not loc or not getattr(loc, "raw", None):
        return None
    raw = loc.raw
    addr = raw.get("address") or {}
    label = build_place_label_from_address(addr, raw.get("display_name"))
    return (label or "").strip() or None


def geocode_place_to_coordinates(place: str) -> tuple[float, float] | None:
    """
    Forward-geocode a city or neighborhood string to (lat, lng) for proximity matching.
    Returns None if not found or on service error.
    """
    q = (place or "").strip()
    if not q:
        return None
    try:
        loc = _get_geolocator().geocode(q, language="en", exactly_one=True, timeout=12)
    except (GeocoderTimedOut, GeocoderServiceError, OSError, ValueError):
        return None
    if not loc or loc.latitude is None or loc.longitude is None:
        return None
    return (float(loc.latitude), float(loc.longitude))
