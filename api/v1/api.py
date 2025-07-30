from fastapi import APIRouter
from api.v1.endpoints import users, properties, page_load, flags, questions, responses, cart, wishlist

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(page_load.router, prefix="/page_load", tags=["page_load"])
api_router.include_router(flags.router, prefix="/flags", tags=["flags"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(responses.router, prefix="/responses", tags=["responses"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(wishlist.router, prefix="/wishlist", tags=["wishlist"]) 