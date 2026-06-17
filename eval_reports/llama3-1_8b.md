# llama3.1:8b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
18.07 seconds

## Thinking / Output

Here's an example of a simple FastAPI CRUD (Create, Read, Update, Delete) system for books:

**`main.py`**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()

# Data model for Book
class Book(BaseModel):
    title: str
    author: str
    publication_date: str

# In-memory data store (replace with a database in production)
books = [
    {"id": 1, "title": "Book 1", "author": "Author 1", "publication_date": "2020-01-01"},
    {"id": 2, "title": "Book 2", "author": "Author 2", "publication_date": "2020-02-02"}
]

# GET /books
@app.get("/books")
async def get_books():
    return books

# GET /books/{book_id}
@app.get("/books/{book_id}")
async def get_book(book_id: int):
    book = next((book for book in books if book["id"] == book_id), None)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

# POST /books
@app.post("/books")
async def create_book(book: Book):
    new_book = {
        "id": len(books) + 1,
        "title": book.title,
        "author": book.author,
        "publication_date": book.publication_date
    }
    books.append(new_book)
    return new_book

# PUT /books/{book_id}
@app.put("/books/{book_id}")
async def update_book(book_id: int, book: Book):
    for existing_book in books:
        if existing_book["id"] == book_id:
            existing_book["title"] = book.title
            existing_book["author"] = book.author
            existing_book["publication_date"] = book.publication_date
            return existing_book

    raise HTTPException(status_code=404, detail="Book not found")

# DELETE /books/{book_id}
@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    for i, book in enumerate(books):
        if book["id"] == book_id:
            del books[i]
            return {"message": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
This example uses the `FastAPI` framework to create a simple CRUD system for books.

**Endpoints**

* **GET /books**: Returns all books
* **GET /books/{book_id}**: Returns a single book by ID
* **POST /books**: Creates a new book
* **PUT /books/{book_id}**: Updates an existing book
* **DELETE /books/{book_id}**: Deletes a book

**Data model**

The `Book` data model is defined using the `pydantic` library. It represents a single book with title, author, and publication date.

**In-memory data store**

For simplicity, this example uses an in-memory data store (`books`) to store the books. In production, you should replace this with a database (e.g., PostgreSQL) to persist data across requests.

To run the API, save this code to `main.py` and execute it using `uvicorn`: `$ uvicorn main:app --host 0.0.0.0 --port 8000`. The API will be available at `http://localhost:8000`.

Note that this is a simplified example and you should consider implementing authentication, authorization, and validation for production use cases.
