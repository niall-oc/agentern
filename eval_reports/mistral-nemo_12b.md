# mistral-nemo:12b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
17.80 seconds

## Thinking / Output

Here's a simple FastAPI application with CRUD operations (Create, Read, Update, Delete) for managing books. We'll use an in-memory database `[]` for demonstration purposes.

```python
from fastapi import FastAPI, HTTPException
from typing import List

app = FastAPI()

# In-memory data store
books = {}

@app.post("/books/", response_model=Book)
def create_book(book: Book):
    if book.id:
        raise HTTPException(status_code=400, detail="ID already provided")
    new_id = len(books) + 1
    book.id = new_id
    books[new_id] = book.dict()
    return book

@app.get("/books/", response_model=List[Book])
def read_all_books():
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

    updated_book.id = book_id
    books[book_id] = updated_book.dict()
    return updated_book

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")

    del books[book_id]
    return {"detail": "Book deleted"}

# Book model
class Book:
    id: int
    title: str
    author: str
    published_year: int

    class Config:
        orm_mode = True
```

To run this FastAPI application, save the code in a file named `main.py` and execute the following commands:

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

Now you can access the API at http://127.0.0.1:8000/ and use the CRUD operations with the `/books/` endpoint.

Here's an example of creating a new book using `curl`:

```bash
curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"title": "The Catcher in the Rye", "author": "J.D. Salinger", "published_year": 1951}' \
    http://127.0.0.1:8000/books/
```
