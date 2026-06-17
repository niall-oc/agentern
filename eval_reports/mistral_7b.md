# mistral:7b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
19.51 seconds

## Thinking / Output

 To create a simple FAST API CRUD (Create, Read, Update, Delete) system for books, follow the steps below:

1. Install fastapi and uvicorn libraries:

```bash
pip install fastapi uvicorn sqlalchemy
```

2. Create a new Python file `main.py` and add the following code:

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author_id = Column(Integer, ForeignKey("authors.id"))

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()

class BookCreate(BaseModel):
    title: str
    author_id: int

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author_id: Optional[int] = None

@app.post("/books/", response_model=Book)
def create_book(book: BookCreate):
    db = SessionLocal()
    author = db.query(Author).filter(Author.id == book.author_id).first()

    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    new_book = Book(title=book.title, author_id=author.id)
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return new_book

@app.get("/books/", response_model=List[Book])
def read_books():
    db = SessionLocal()
    books = db.query(Book).all()
    return books

@app.get("/books/{book_id}", response_model=Book)
def read_book(book_id: int):
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate):
    db = SessionLocal()
    book_query = db.query(Book).filter(Book.id == book_id)
    book_exists = book_query.first()

    if not book_exists:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.title:
        book_query.update({Book.title: book.title})

    if book.author_id:
        author = db.query(Author).filter(Author.id == book.author_id).first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        book_query.update({Book.author_id: author.id})

    db.commit()
    db.refresh(book_query.first())
    return book_query.first()

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

3. Run the application:

```bash
uvicorn main:app --reload
```

Now you have a simple FAST API CRUD system for books using SQLite as the database. You can use tools like Postman or CURL to test the endpoints.
