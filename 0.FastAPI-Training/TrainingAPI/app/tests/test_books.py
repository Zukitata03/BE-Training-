import pytest


@pytest.mark.anyio
async def test_get_books_unauthorized(client):
    resp = await client.get("/api/v1/books/")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_create_and_get_books(auth_client):
    resp = await auth_client.post(
        "/api/v1/books/",
        json={"title": "Test Book", "author": "Test Author", "description": "A test"},
    )
    assert resp.status_code == 201
    book = resp.json()
    assert book["title"] == "Test Book"
    assert book["author"] == "Test Author"
    book_id = book["id"]

    resp = await auth_client.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Book"


@pytest.mark.anyio
async def test_list_books_paginated(auth_client):
    for i in range(5):
        await auth_client.post(
            "/api/v1/books/",
            json={"title": f"Book {i}", "author": f"Author {i}"},
        )
    resp = await auth_client.get("/api/v1/books/?page=1&page_size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) <= 3
    assert data["total"] >= 5
    assert data["page"] == 1


@pytest.mark.anyio
async def test_update_book(auth_client):
    resp = await auth_client.post(
        "/api/v1/books/",
        json={"title": "Old Title", "author": "Author"},
    )
    book_id = resp.json()["id"]
    resp = await auth_client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.anyio
async def test_delete_book(auth_client):
    resp = await auth_client.post(
        "/api/v1/books/",
        json={"title": "Delete Me", "author": "Author"},
    )
    book_id = resp.json()["id"]
    resp = await auth_client.delete(f"/api/v1/books/{book_id}")
    assert resp.status_code == 204
    resp = await auth_client.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 404
