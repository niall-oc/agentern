# qwen2.5-coder:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
18.98 seconds

## Thinking / Output

Creating a simple FastAPI CRUD (Create, Read, Update, Delete) system for managing books involves several steps. Below is a step-by-step guide to help you set up the project.

### Step 1: Set Up Your Project

First, create a new directory for your project and navigate into it:

```bash
mkdir fastapi_crud_books
cd fastapi_crud_books
```

Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install FastAPI and Uvicorn (a web server for running FastAPI applications):

```bash
pip install fastapi uvicorn
```

### Step 2: Create the Project Structure

Create a directory structure for your project:

```
fastapi_crud_books/
├── main.py
└── requirements.txt
```

### Step 3: Define the Book Model

In `main.py`, define a simple Pydantic model for the book:

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
    published_year: Optional[int] = None
```

### Step 4: Implement CRUD Operations

Add the following routes to handle CRUD operations:

```python
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

@app.delete("/books/{book_id}", response_model=bool)
def delete_book(book_id: int):
    global books_db
    books_db = [b for b in books_db if b.id != book_id]
    return True
```

### Step 5: Run the Application

Run your FastAPI application using Uvicorn:

```bash
uvicorn main:app --reload
```

The `--reload` flag will automatically reload the server when you make changes to your code.

### Step 6: Test the API

You can test the API using tools like Postman or curl. Here are some example requests:

- **Create a book**:
  ```bash
  curl -X POST "http://127.0.0.1:8000/books/" -H "Content-Type: application/json" -d '{"id": 1, "title": "Book Title", "author": "Author Name"}'
  ```

- **Read all books**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/books/"
  ```

- **Read a single book**:
  ```bash
  curl -X GET "http://127.0.0.1:8000/books/1"
  ```

- **Update a book**:
  ```bash
  curl -X PUT "http://127.0.0.1:8000/books/1" -H "Content-Type: application/json" -d '{"id": 1, "title": "Updated Title", "author": "Author Name"}'
  ```

- **Delete a book**:
  ```bash
  curl -X DELETE "http://127.0.0.1:8000/books/1"
  ```

### Step 7: (Optional) Create a Documentation

FastAPI automatically generates interactive API documentation using Swagger UI and ReDoc:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

You can use these interfaces to test your API without writing any code.

That's it! You now have a simple FastAPI CRUD system for managing books.
