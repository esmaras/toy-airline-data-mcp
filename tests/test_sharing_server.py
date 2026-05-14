"""
Tests for the Delta Sharing FastAPI server.
Uses httpx AsyncClient against the app directly — no real Delta tables needed
for structure tests.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from sharing.server import app


@pytest.mark.asyncio
async def test_list_shares_returns_json():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/shares")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_list_schemas_known_share():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/shares/southwest_airline/schemas")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    schema_names = [s["name"] for s in data["items"]]
    assert "schedules" in schema_names


@pytest.mark.asyncio
async def test_list_tables_known_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/shares/southwest_airline/schemas/schedules/tables")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_unknown_share_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/shares/does_not_exist/schemas")
    assert response.status_code == 404
