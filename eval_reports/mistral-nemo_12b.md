# mistral-nemo:12b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
18.07 seconds

## Thinking / Output

Here's a simple FastAPI CRUD (Create, Read, Update, Delete) system for managing books. This example uses `uvicorn` as the ASGI server and `fastapi` with `pydantic` for creating models, and in-memory storage for simplicity.

First, make sure you have FastAPI installed:

```bash
pip install fastapi uvicorn pydantic
```

Now, create a new file named `main.py`:

```python
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# In-memory storage for books.
books = {}

class Book(BaseModel):
    id: int
    title: str
    author: str
    publication_year: int

@app.post("/books/", response_model=Book)
def create_book(book: Book):
    if book.id in books:
        raise HTTPException(status_code=400, detail="ID already exists")
    books[book.id] = book
    return book

@app.get("/books/", response_model=List[Book])
def read_books():
    return list(books.values())

@app.get("/books/{book_id}", response_model=Book)
def read_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, updated_book: Book):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    books[book_id] = updated_book
    return updated_book

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    del books[book_id]
    return {"detail": "Book deleted"}
```

To run the API, use the following command:

```bash
uvicorn main:app --reload
```

Now you can interact with your CRUD system using an API client like `curl`, Postman, or HTTPie.

Here's an example using `curl` to create a new book:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"id": 1, "title": "The Catcher in the Rye", "author": "J.D. Salinger", "publication_year": 1951}' \
  http://localhost:8000/books/
```
