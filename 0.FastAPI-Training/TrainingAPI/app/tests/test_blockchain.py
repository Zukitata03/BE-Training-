import pytest


@pytest.mark.anyio
async def test_get_events_unauthorized(client):
    resp = await client.get("/api/v1/blockchain/events")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_index_contract_unauthorized(client):
    resp = await client.post(
        "/api/v1/blockchain/index",
        params={"contract_address": "0x1234567890123456789012345678901234567890"},
    )
    assert resp.status_code == 401
