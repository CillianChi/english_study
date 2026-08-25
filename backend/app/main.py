from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, game, review

app = FastAPI(title="TOEIC 背單字 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real frontend origin before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(review.router)
app.include_router(game.router)


@app.get("/health")
def health():
    return {"status": "ok"}
