from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.property.api import router as property_router
from app.property import wishlist_router, cart_router

def create_app():
    app = FastAPI(
        title="Property API"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include property router
    app.include_router(property_router, prefix="/api", tags=["properties"])
    app.include_router(wishlist_router, prefix="/api")
    app.include_router(cart_router, prefix="/api")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
