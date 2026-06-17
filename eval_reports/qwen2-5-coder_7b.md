# qwen2.5-coder:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
13.83 seconds

## Thinking / Output

Creating a simple CRUD (Create, Read, Update, Delete) system for books using FastAPI is quite straightforward. Below is an example of how you can implement this.

First, make sure you have FastAPI and Uvicorn installed. You can install them using pip:

```bash
pip install fastapi uvicorn
```

Next, create a file named `main.py` and add the following code:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# In-memory database simulation
books_db = []

class Book(BaseModel):
    id: int
    title: str
    author: str
    published_year: int
    is_available: bool = True

@app.post("/books/", response_model=Book)
def create_book(book: Book):
    books_db.append(book)
    return book

@app.get("/books/", response_model=List[Book])
def read_books():
    return books_db

@app.get("/books/{book_id}", response_model=Book)
def read_book(book_id: int):
    for book in books_db:
        if book.id == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: Book):
    for i, b in enumerate(books_db):
        if b.id == book_id:
            books_db[i] = book
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/books/{book_id}", response_model=Book)
def delete_book(book_id: int):
    for i, b in enumerate(books_db):
        if b.id == book_id:
            removed_book = books_db.pop(i)
            return removed_book
    raise HTTPException(status_code=404, detail="Book not found")

# Example of adding a book to the database
@app.on_event("startup")
async def startup_event():
    books_db.append(Book(id=1, title="1984", author="George Orwell", published_year=1949))
```

This code sets up a simple CRUD system for books. Here's a brief explanation of each endpoint:

- `POST /books/`: Creates a new book.
- `GET /books/`: Retrieves all books.
- `GET /books/{book_id}`: Retrieves a specific book by its ID.
- `PUT /books/{book_id}`: Updates an existing book.
- `DELETE /books/{book_id}`: Deletes an existing book.

To run the application, use the following command:

```bash
uvicorn main:app --reload
```

This will start the FastAPI server on `http://127.0.0.1:8000/`. You can then test the endpoints using tools like Postman or curl.

For example, to create a new book, you can use:

```bash
curl -X POST "http://127.0.0.1:8000/books/" -H "Content-Type: application/json" -d '{"id": 2, "title": "To Kill a Mockingbird", "author": "Harper Lee", "published_year": 1960}'
```

And to retrieve all books:

```bash
curl "http://127.0.0.1:8000/books/"
```

This is a basic implementation and does not include database persistence or advanced features like authentication and authorization. For production use, you would typically integrate with a real database and consider additional security measures.
