from typing import Union # for type checking
from fastapi import FastAPI


app = FastAPI()

@app.get("/")
async def read_root():
    return {"message" : "Backend team is best"}


