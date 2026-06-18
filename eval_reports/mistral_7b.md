# mistral:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
18.53 seconds

## Thinking / Output

 To create a simple FASTAPI CRUD (Create, Read, Update, Delete) system for books, follow the steps below:

1. Install FastAPI and Uvicorn:

```bash
pip install fastapi uvicorn
```

2. Create a new file named `main.py`, and add the following code:

```python
from fastapi import FastAPI, HTTP_CONTENT_TYPES, Response
from pydantic import BaseModel
from typing import List, Optional
import random
import uuid

app = FastAPI()

class Book(BaseModel):
    id: str = None
    title: str
    author: str
    pages: int
    published_year: int

books = []

def get_book_by_id(book_id: str) -> Optional[Book]:
    return next((book for book in books if book.id == book_id), None)

@app.get("/", response_class=Response)
async def read_root():
    return {"Hello": "World"}

@app.post("/books/", response_model=Book)
def create_book(book: Book):
    book.id = str(uuid.uuid4())
    books.append(book)
    return book

@app.get("/books/{book_id}", response_model=Optional[Book])
def read_book(book_id: str):
    book = get_book_by_id(book_id)
    if not book:
        return None
    return book

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: str, updated_book: Book):
    existing_book = get_book_by_id(book_id)
    if not existing_book:
        return None
    index = books.index(existing_book)
    books[index] = updated_book
    return updated_book

@app.delete("/books/{book_id}")
def delete_book(book_id: str):
    book = get_book_by_id(book_id)
    if not book:
        return None
    books.remove(book)
    return {"result": "Book deleted"}
```

3. Run the application using Uvicorn:

```bash
uvicorn main:app --reload
```

4. Access the FastAPI endpoints at `http://127.0.0.1:8000`.

You can now create, read, update and delete books using HTTP requests. To test it using curl or Postman, use the following examples:

- Create a new book:

```bash
curl -X POST "http://127.0.0.1:8000/books/" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"The Catcher in the Rye\",
    \"author\": \"J.D. Salinger\",
    \"pages\": 277,
    \"published_year\": 1951
}"
```

- Read all books:

```bash
curl "http://127.0.0.1:8000/books/"
```

- Read a specific book by id:

```bash
curl "http://127.0.0.1:8000/books/<book_id>"
```

- Update a specific book by id:

```bash
curl -X PUT "http://127.0.0.1:8000/books/<book_id>" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"New Title\",
    \"author\": \"New Author\",
    \"pages\": 300,
    \"published_year\": 2022
}"
```

- Delete a specific book by id:

```bash
curl -X DELETE "http://127.0.0.1:8000/books/<book_id>"
```
