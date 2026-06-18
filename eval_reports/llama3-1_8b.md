# llama3.1:8b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
16.44 seconds

## Thinking / Output

Below is an example of how you can implement a basic CRUD (Create, Read, Update, Delete) system for books using FastAPI. This system includes endpoints for:

- Creating a new book (`POST /books`)
- Retrieving all books (`GET /books`)
- Retrieving a specific book by ID (`GET /books/{book_id}`)
- Updating an existing book (`PUT /books/{book_id}`)
- Deleting a book (`DELETE /books/{book_id}`)

First, ensure you have FastAPI and Uvicorn installed. You can install them via pip:

```bash
pip install fastapi uvicorn
```

Now, let's write the code for the API:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Book(BaseModel):
    title: str
    author: str
    publication_date: str
    pages: int

# Sample in-memory data store (for demonstration purposes)
books = [
    {"id": 1, "title": "Book 1", "author": "Author A", "publication_date": "2022-01-01", "pages": 200},
    {"id": 2, "title": "Book 2", "author": "Author B", "publication_date": "2020-06-01", "pages": 250}
]

# Endpoint to create a new book
@app.post("/books")
async def create_book(book: Book):
    books.append({"id": len(books) + 1, **book.dict()})
    return {"message": f"Book '{book.title}' created successfully"}

# Endpoint to get all books
@app.get("/books")
async def read_books():
    return [{"id": book["id"], "title": book["title"]} for book in books]

# Endpoint to retrieve a specific book by ID
@app.get("/books/{book_id}")
async def read_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return {"id": book["id"], "title": book["title"]}
    return {"message": f"Book with ID {book_id} not found"}

# Endpoint to update an existing book
@app.put("/books/{book_id}")
async def update_book(book_id: int, book: Book):
    for existing_book in books:
        if existing_book["id"] == book_id:
            existing_book.update(book.dict())
            return {"message": f"Book with ID {book_id} updated successfully"}
    return {"message": f"Book with ID {book_id} not found"}

# Endpoint to delete a book
@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    for i, existing_book in enumerate(books):
        if existing_book["id"] == book_id:
            del books[i]
            return {"message": f"Book with ID {book_id} deleted successfully"}
    return {"message": f"Book with ID {book_id} not found"}
```

This example uses a simple in-memory data store (`books` list) for demonstration purposes. In a real-world application, you would replace this with a database like SQLite or PostgreSQL.

To run the API, execute the following command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Replace `main` with your actual Python file name if it differs. Now you can use tools like curl or a REST client (e.g., Postman) to interact with the API.

Example usage:

- Create a new book: `curl -X POST http://localhost:8000/books -H 'Content-Type: application/json' -d '{"title": "New Book", "author": "Author C", "publication_date": "2023-02-01", "pages": 300}'`
- Get all books: `curl http://localhost:8000/books`
- Retrieve a specific book by ID: `curl http://localhost:8000/books/1`
