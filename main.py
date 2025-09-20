from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message" : "Backend team is worst"}