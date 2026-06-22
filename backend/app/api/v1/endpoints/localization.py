"""Localization reference-data endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.localization import MarketProfileResponse
from app.services.localization_service import get_market_profile, list_market_profiles

router = APIRouter()


@router.get("/market-profiles", response_model=list[MarketProfileResponse])
async def get_market_profiles() -> list[MarketProfileResponse]:
    """Return public launch-market localization profiles."""
    return list_market_profiles()


@router.get("/market-profiles/{country_or_market}", response_model=MarketProfileResponse)
async def get_market_profile_endpoint(country_or_market: str) -> MarketProfileResponse:
    """Return one launch-market profile by country or product market code."""
    profile = get_market_profile(country_or_market)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market profile not found",
        )
    return profile
