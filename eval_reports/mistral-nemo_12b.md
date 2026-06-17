# mistral-nemo:12b — Evaluation

## Prompt
Create a simple FAST API CRUD system for books

## Runtime
18.79 seconds

## Thinking / Output

Here's a simple FastAPI CRUD (Create, Read, Update, Delete) system for books. This example uses `uvicorn` as the ASGI server and `python-dotenv` to manage environment variables like the database URL.

First, install the required packages:

```bash
pip install fastapi uvicorn python-dotenv tortoise-orm asyncpg
```

Now, create a `.env` file in your project root with the following content (replace the values with your own database credentials):

```
DATABASE_URL=postgres://username:password@localhost/db_name
```

Create a `main.py` file and add the following code:

```python
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tortoise import fields, models
from tortoise.orm import init_tortoise_db, generate_schema
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

class Book(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(50)
    author = fields.CharField(50)
    published_year = fields.IntField()

    class PydanticMeta:
        exclude = ["id"]

class BookIn(BaseModel):
    title: str
    author: str
    published_year: int

async def init_db():
    await init_tortoise_db(
        db_url=DATABASE_URL,
        modules={"models": __name__},
        generate_schemas=True
    )

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/books/")
async def create_book(book: BookIn):
    new_book = await Book.create(**book.dict())
    return {"id": new_book.id, **new_book.__dict__}

@app.get("/books/{book_id}")
async def get_book(book_id: int):
    book = await Book.filter(id=book_id).first_or_404()
    return {"id": book.id, **book.__dict__}

@app.put("/books/{book_id}")
async def update_book(book_id: int, updated_book: BookIn):
    book = await Book.filter(id=book_id).first_or_404()

    for key, value in updated_book.dict().items():
        setattr(book, key, value)

    await book.save()
    return {"id": book.id, **book.__dict__}

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    book = await Book.filter(id=book_id).first_or_404()
    await book.delete()
    return {"detail": "Book deleted"}
```

Finally, run the application using:

```bash
uvicorn main:app --reload
```

Now you have a simple FastAPI CRUD system for books running at `http://127.0.0.1:8000/`.

You can test it using tools like [Postman](https://www.postman.com/) or [curl](https://curl.se/).
