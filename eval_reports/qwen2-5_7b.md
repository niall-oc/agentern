# qwen2.5:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
19.91 seconds

## Thinking / Output

Sure! Below is a basic example of how you can create a CRUD (Create, Read, Update, Delete) system for managing books using FastAPI and Python.

First, make sure you have the necessary dependencies installed:

```sh
pip install fastapi uvicorn
```

Then, you can create a simple FastAPI application as follows:

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

@app.post("/books/", response_model=Book)
async def create_book(book: Book):
    books_db.append(book.dict())
    return book

@app.get("/books/", response_model=List[Book])
async def read_books():
    return books_db

@app.get("/books/{book_id}", response_model=Book)
async def read_book(book_id: int):
    for book in books_db:
        if book['id'] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, updated_book: Book):
    for index, book in enumerate(books_db):
        if book['id'] == book_id:
            books_db[index] = updated_book.dict()
            return updated_book
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/books/{book_id}", response_model=None)
async def delete_book(book_id: int):
    for index, book in enumerate(books_db):
        if book['id'] == book_id:
            del books_db[index]
            return {"detail": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### Explanation

- **Book Model**: A Pydantic model `Book` is defined to represent the structure of a book with fields like `id`, `title`, `author`, and `published_year`.
  
- **Create Book** (`/books/` POST): Adds a new book to the in-memory database.

- **Read Books** (`/books/` GET): Returns all books in the database.

- **Read Book by ID** (`/books/{book_id}` GET): Retrieves a single book by its ID. Raises an HTTP 404 error if the book is not found.

- **Update Book** (`/books/{book_id}` PUT): Updates a book with new data. Raises an HTTP 404 error if the book is not found.

- **Delete Book** (`/books/{book_id}` DELETE): Deletes a book by its ID. Raises an HTTP 404 error if the book is not found.

### Running the Application

To run the FastAPI application, you can use the following command:

```sh
uvicorn main:app --reload
```

Replace `main` with the name of your Python script file (e.g., `fastapi_crud.py`). The `--reload` flag allows you to automatically reload the server when changes are made to the code.

You can now test your API using tools like `curl`, Postman, or any other HTTP client. Here's an example of how to use `curl`:

- Create a book:
  ```sh
  curl -X POST "http://127.0.0.1:8000/books/" -H "Content-Type: application/json" -d '{"id": 1, "title": "The Catcher in the Rye", "author": "J.D. Salinger", "published_year": 1951}'
  ```

- Get all books:
  ```sh
  curl "http://127.0.0.1:8000/books/"
  ```

- Update a book:
  ```sh
  curl -X PUT "http://127.0.0.1:8000/books/1" -H "Content-Type: application/json" -d '{"id": 1, "title": "To Kill a Mockingbird", "author": "Harper Lee", "published_year": 1960}'
  ```

- Delete a book:
  ```sh
  curl -X DELETE "http://127.0.0.1:8000/books/1"
  ```

This is a very simple and basic implementation, but it should give you a good starting point for building more complex applications with FastAPI.
