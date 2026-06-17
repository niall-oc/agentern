# llama3.1:8b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
20.44 seconds

## Thinking / Output

Here's an example of a simple CRUD (Create, Read, Update, Delete) system using FastAPI and PostgreSQL as the database. We will use SQLAlchemy for interacting with the database.

Firstly, make sure you have the necessary packages installed:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart
```

**`main.py`**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Import database utilities
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Initialize the engine with the URL to your PostgreSQL database
engine = create_engine('postgresql://user:password@localhost/database')

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base metadata for our models
Base = declarative_base()

class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    author = Column(String)

@app.get("/books/", response_model=List[dict])
def read_books():
    """Get all books."""
    db = SessionLocal()
    try:
        return db.query(Book).all()
    finally:
        db.close()

@app.post("/books/")
def create_book(new_book: dict):
    """Create a new book."""
    db = SessionLocal()
    try:
        db.add(Book(title=new_book['title'], author=new_book['author']))
        db.commit()
        return {"message": "Book created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@app.get("/books/{book_id}", response_model=dict)
def read_book(book_id: int):
    """Get a book by ID."""
    db = SessionLocal()
    try:
        return db.query(Book).filter(Book.id == book_id).first()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()

@app.put("/books/{book_id}")
def update_book(book_id: int, updated_book: dict):
    """Update a book by ID."""
    db = SessionLocal()
    try:
        existing_book = db.query(Book).filter(Book.id == book_id).first()
        if not existing_book:
            raise HTTPException(status_code=404, detail="Book not found")
        existing_book.title = updated_book['title']
        existing_book.author = updated_book['author']
        db.commit()
        return {"message": "Book updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    """Delete a book by ID."""
    db = SessionLocal()
    try:
        existing_book = db.query(Book).filter(Book.id == book_id).first()
        if not existing_book:
            raise HTTPException(status_code=404, detail="Book not found")
        db.delete(existing_book)
        db.commit()
        return {"message": "Book deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

# Base.metadata.create_all(engine)
```

**`requirements.txt`**
```bash
fastapi uvicorn sqlalchemy psycopg2-binary python-multipart
```
This will create a basic CRUD system with the following endpoints:

*   `GET /books/`: Returns all books.
*   `POST /books/`: Creates a new book. The request body must be in JSON format, e.g., `{ "title": "Book Title", "author": "Author Name" }`.
*   `GET /books/{book_id}`: Retrieves a book by ID.
*   `PUT /books/{book_id}`: Updates an existing book. The request body must be in JSON format with the updated values.
*   `DELETE /books/{book_id}`: Deletes a book.

To run this code, use:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
You can then access these endpoints by navigating to `http://localhost:8000/docs` in your web browser or using tools like `curl` for testing.

Note that you need to replace the placeholders in `create_engine` with your actual PostgreSQL credentials and database name. Also, consider setting up a proper development environment with dependencies managed via pip. This is just a minimal example to demonstrate CRUD operations with FastAPI and SQLAlchemy.
