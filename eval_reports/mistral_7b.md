# mistral:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
20.33 seconds

## Thinking / Output

 To create a simple FASTAPI CRUD system for books, I will use SQLAlchemy as the ORM to interact with the database and PostgreSQL as the database. Here's how you can set it up:

1. Install necessary dependencies:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary
```

2. Create a file named `main.py` and paste the following code:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()

DATABASE_URL = "postgresql://username:password@localhost/dbname"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
Base = declarative_base()

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    published_date = Column(DateTime, index=True)

Base.metadata.create_all(bind=engine)

class BookCreate(BaseModel):
    title: str
    author: str
    published_date: datetime

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None

@app.post("/books/", response_model=Book)
def create_book(book: BookCreate):
    db = SessionLocal()
    new_book = Book(**book.dict())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@app.get("/books/", response_model=list[Book])
def read_books(skip: int = 0, limit: int = 10):
    db = SessionLocal()
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{book_id}", response_model=Book)
def read_book(book_id: int):
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book_update: BookUpdate):
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.title = book_update.title or book.title
    book.author = book_update.author or book.author
    book.published_date = book_update.published_date or book.published_date

    db.commit()
    db.refresh(book)
    return book

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()
    return {"detail": "Book deleted"}
```

Replace `username`, `password`, and `dbname` in the `DATABASE_URL` variable with your own PostgreSQL credentials and database name.

3. To run the application:

```bash
uvicorn main:app --reload
```

Now you have a simple FASTAPI CRUD system for books that can perform create, read, update, and delete operations on your PostgreSQL database. You can test the API by using tools like curl or Postman to interact with the endpoints provided in the code above.
