# qwen2.5-coder:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
14.16 seconds

## Thinking / Output

To create a simple FastAPI CRUD (Create, Read, Update, Delete) system for books, you can follow these steps:

1. **Set up your environment**:
   - Install Python if it's not already installed.
   - Create a virtual environment and activate it.
   - Install FastAPI and Uvicorn using pip.

2. **Create the project structure**:
   ```
   book_crud/
   ├── main.py
   └── models.py
   ```

3. **Define the model (models.py)**:
   ```python
   from pydantic import BaseModel

   class Book(BaseModel):
       id: int
       title: str
       author: str
       published_year: int
   ```

4. **Create the main application (main.py)**:
   ```python
   from fastapi import FastAPI, HTTPException
   from typing import List, Optional

   app = FastAPI()

   # In-memory "database" for demonstration purposes
   books_db = [
       Book(id=1, title="1984", author="George Orwell", published_year=1949),
       Book(id=2, title="To Kill a Mockingbird", author="Harper Lee", published_year=1960)
   ]

   @app.get("/books/", response_model=List[Book])
   def read_books():
       return books_db

   @app.post("/books/", response_model=Book)
   def create_book(book: Book):
       books_db.append(book)
       return book

   @app.get("/books/{book_id}", response_model=Book)
   def read_book(book_id: int):
       for book in books_db:
           if book.id == book_id:
               return book
       raise HTTPException(status_code=404, detail="Book not found")

   @app.put("/books/{book_id}", response_model=Book)
   def update_book(book_id: int, updated_book: Book):
       for idx, book in enumerate(books_db):
           if book.id == book_id:
               books_db[idx] = updated_book
               return updated_book
       raise HTTPException(status_code=404, detail="Book not found")

   @app.delete("/books/{book_id}", response_model=Book)
   def delete_book(book_id: int):
       for idx, book in enumerate(books_db):
           if book.id == book_id:
               deleted_book = books_db.pop(idx)
               return deleted_book
       raise HTTPException(status_code=404, detail="Book not found")
   ```

5. **Run the application**:
   ```
   uvicorn main:app --reload
   ```

This code sets up a basic FastAPI CRUD system for managing books. It uses an in-memory list to store book data and provides endpoints to create, read, update, and delete books.

To test the API, you can use tools like Postman or curl:
- To get all books: `GET http://127.0.0.1:8000/books/`
- To create a new book: `POST http://127.0.0.1:8000/books/` with JSON body
- To update a book: `PUT http://127.0.0.1:8000/books/{book_id}` with JSON body
- To delete a book: `DELETE http://127.0.0.1:8000/books/{book_id}`

Remember to replace `{book_id}` with the actual ID of the book you want to interact with.
