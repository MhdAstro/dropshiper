from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_platforms():
    return {"message": "Get platforms endpoint - to be implemented"}


@router.post("/")
async def create_platform():
    return {"message": "Create platform endpoint - to be implemented"}