# deepseek-coder:6.7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
11.51 seconds

## Thinking / Output

Sure, I'll provide a basic example of how you could set up an API with FastAPI that allows you to perform Create (POST), Read (GET), Update (PUT) and Delete (DELETE) operations on book data. 

```python
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Define the Book model using Pydantic's BaseModel
class Book(BaseModel):
    id: int
    title: str
    author: str
    year_published: Optional[int] = None

# Mock data
books = {
    1: {"id": 1, "title": "Book One", "author": "Author One", "year_published": 2001},
    2: {"id": 2, "title": "Book Two", "author": "Author Two", "year_published": 2002},
}

@app.get("/books/")
async def read_all():
    return books


@app.post("/books/")
async def create(book: Book):
    new_id = max(books.keys()) + 1
    book.id = new_id
    books[new_id] = book
    return books


@app.get("/books/{book_id}")
async def read(book_id: int):
    return books.get(book_id)


@app.put("/books/")
async def update(updated_book: Book):
    if updated_book.id in books:
        books[updated_book.id] = updated_book
        return {"Success": f"Updated book with id {updated_book.id}"}
    else:
        return {"Error": "Book not found"}

@app.delete("/books/{book_id}")
async def delete(book_id: int):
    if book_id in books:
        del books[book_id]
        return {"Success": f"Deleted book with id {book_id}"}
    else:
        return {"Error": "Book not found"}

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)
```

This is a very basic implementation and does not include any sort of persistent data storage or error handling beyond what FastAPI provides out of the box (e.g., no validation for non-integer ids in `/books/{book_id}`). For full CRUD functionality, you'd likely want to replace `books` with a database and add more robust error handling.

