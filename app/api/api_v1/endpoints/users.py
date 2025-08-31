from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_users():
    return {"message": "Get users endpoint - to be implemented"}


@router.post("/")
async def create_user():
    return {"message": "Create user endpoint - to be implemented"}