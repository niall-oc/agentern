# qwen2.5:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
21.95 seconds

## Thinking / Output

Certainly! Below is an example of a simple CRUD (Create, Read, Update, Delete) system using FastAPI and SQLAlchemy with an SQLite database. This example includes basic book management operations such as creating a book, reading all or specific books, updating a book, and deleting a book.

First, ensure you have the necessary packages installed:

```bash
pip install fastapi uvicorn sqlalchemy databases
```

Next, create your FastAPI application with SQLAlchemy integration for handling database operations. Here's a complete example:

### `main.py`

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    published_year = Column(Integer)

# Pydantic models
class BookCreate(BaseModel):
    title: str
    author: str
    published_year: int

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    published_year: Optional[int] = None

app = FastAPI()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD Operations

@app.post("/books/", response_model=Book)
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    new_book = Book(**book.dict())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@app.get("/books/", response_model=List[Book])
async def read_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{book_id}", response_model=Book)
async def read_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    for key, value in book_update.dict().items():
        setattr(book, key, value) if value else None
    
    db.commit()
    db.refresh(book)
    return book

@app.delete("/books/{book_id}", response_model=dict)
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}
```

### Running the Application

To run the application, use the following command:

```bash
uvicorn main:app --reload
```

This will start a development server that you can access at `http://127.0.0.1:8000`.

### Sample API Endpoints

- **Create a Book**:
  - Method: POST
  - URL: `/books/`
  - Example request body:
    ```json
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "published_year": 1925
    }
    ```

- **Read All Books**:
  - Method: GET
  - URL: `/books/`
  - Optional query parameters: `skip`, `limit` (default is 100).

- **Read a Specific Book by ID**:
  - Method: GET
  - URL: `/books/{book_id}`
  - Example request body for fetching book with id=1: `/books/1`

- **Update a Book**:
  - Method: PUT
  - URL: `/books/{book_id}`
  - Example request body (to update title and author):
    ```json
    {
        "title": "The Catcher in the Rye",
        "author": "J.D. Salinger"
    }
    ```

- **Delete a Book**:
  - Method: DELETE
  - URL: `/books/{book_id}`
  - Example request body (to delete book with id=1): `/books/1`

This setup provides a basic CRUD application for managing books using FastAPI and SQLAlchemy. You can extend this example to include more features like pagination, sorting, etc., as needed.
