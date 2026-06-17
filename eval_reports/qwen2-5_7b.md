# qwen2.5:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
19.19 seconds

## Thinking / Output

Sure! Below is an example of how to create a simple CRUD (Create, Read, Update, Delete) system using FastAPI and Pydantic in Python. This example will demonstrate the basic operations on a `Book` model.

First, ensure you have the necessary libraries installed:

```bash
pip install fastapi uvicorn pydantic
```

Here is a complete example:

1. **Define the Book Model:**

   Create a file named `models.py`:

   ```python
   from datetime import datetime
   from typing import Optional

   from pydantic import BaseModel, EmailStr

   class BookBase(BaseModel):
       title: str
       author: str
       published_date: datetime = datetime.now()
       description: Optional[str] = None

   class BookCreate(BookBase):
       pass

   class BookUpdate(BookBase):
       id: int

   class Book(BookBase):
       id: int
       owner_email: EmailStr

       class Config:
           orm_mode = True
   ```

2. **Define the CRUD Operations:**

   Create a file named `book_service.py`:

   ```python
   from typing import List, Optional
   from datetime import datetime
   from models import BookBase, BookCreate, BookUpdate, Book

   class BookService:
       def __init__(self):
           self.books = {}

       def create_book(self, book: BookCreate) -> Book:
           new_book_id = len(self.books) + 1
           new_book = Book(id=new_book_id, **book.dict())
           self.books[new_book_id] = new_book
           return new_book

       def get_books(self) -> List[Book]:
           return list(self.books.values())

       def get_book(self, book_id: int) -> Optional[Book]:
           return self.books.get(book_id)

       def update_book(self, book_id: int, book_update: BookUpdate) -> Optional[Book]:
           if (book := self.get_book(book_id)) is None:
               return None
           updated_data = {**book.dict(), **book_update.dict(exclude_unset=True)}
           self.books[book_id] = Book(id=book_id, **updated_data)
           return self.books[book_id]

       def delete_book(self, book_id: int) -> Optional[Book]:
           if (book := self.get_book(book_id)) is None:
               return None
           del self.books[book_id]
           return book
   ```

3. **Create the FastAPI Application:**

   Create a file named `main.py`:

   ```python
   from fastapi import FastAPI, HTTPException
   from pydantic import EmailStr
   from book_service import BookService

   app = FastAPI()
   book_service = BookService()

   @app.post("/books/", response_model=Book)
   def create_book(book: BookCreate):
       return book_service.create_book(book)

   @app.get("/books/", response_model=List[Book])
   def read_books():
       return book_service.get_books()

   @app.get("/books/{book_id}", response_model=Book)
   def read_book(book_id: int):
       book = book_service.get_book(book_id)
       if not book:
           raise HTTPException(status_code=404, detail="Book not found")
       return book

   @app.put("/books/{book_id}", response_model=Book)
   def update_book(book_id: int, book_update: BookUpdate):
       updated_book = book_service.update_book(book_id, book_update)
       if not updated_book:
           raise HTTPException(status_code=404, detail="Book not found")
       return updated_book

   @app.delete("/books/{book_id}", response_model=Optional[Book])
   def delete_book(book_id: int):
       deleted_book = book_service.delete_book(book_id)
       if not deleted_book:
           raise HTTPException(status_code=404, detail="Book not found")
       return deleted_book
   ```

4. **Run the Application:**

   You can run the FastAPI application using `uvicorn`:

   ```bash
   uvicorn main:app --reload
   ```

Now you have a simple CRUD system for books that allows you to create, read, update, and delete book records.

To test this API, you can use tools like Postman or curl. For example, to create a new book:

```curl
POST http://127.0.0.1:8000/books/
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald"
}
```

This should help you get started with a basic CRUD system in FastAPI!
