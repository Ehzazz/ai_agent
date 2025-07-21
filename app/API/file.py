from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .db import get_db
from .models import Session, UserFile
from utils.embedding_utils import embed_pdf, embed_docx, embed_ppt
from utils.file_processing import get_file_type, process_file
from utils.vectorstore_utils import delete_vectors_for_file
import io

router = APIRouter()

@router.post("/upload-and-embed")
async def upload_and_embed(session_token: str = Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    user_id = session.user_id
    filename = file.filename
    content = await file.read()
    file_type = get_file_type(filename, content)
    if file_type not in ['pdf', 'docx', 'ppt']:
        return JSONResponse({"message": "Only PDF, DOCX, and PPT/PPTX files are supported at this time."}, status_code=400)

    user_file = UserFile(
        user_id=user_id,
        file_name=filename,
        file_type=file.content_type,
        file_data=content
    )
    db.add(user_file)
    await db.commit()

    try:
        pages = process_file(filename, content)
        if file_type == 'pdf':
            embed_pdf(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        elif file_type == 'docx':
            embed_docx(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        elif file_type == 'ppt':
            embed_ppt(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        return {"message": f"✅ File '{filename}' uploaded & embedded successfully."}
    except Exception as e:
        import traceback
        print("Exception during file processing:", e)
        traceback.print_exc()
        return JSONResponse({"message": f"File processing failed: {str(e)}"}, status_code=400)

@router.get("/files")
async def list_files(session_token: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    user_id = session.user_id
    result = await db.execute(select(UserFile).where(UserFile.user_id == user_id))
    files = result.scalars().all()
    return [{"id": str(f.id), "file_name": f.file_name, "file_type": f.file_type} for f in files]

@router.delete("/file/{file_id}")
async def delete_file(file_id: str = Path(...), session_token: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    user_id = session.user_id
    result = await db.execute(select(UserFile).where(UserFile.id == file_id, UserFile.user_id == user_id))
    user_file = result.scalar_one_or_none()
    if not user_file:
        raise HTTPException(status_code=404, detail="File not found")
    # Delete vector embeddings for this file
    delete_vectors_for_file(user_id=user_id, file_name=user_file.file_name)
    await db.delete(user_file)
    await db.commit()
    return {"message": f"✅ File '{user_file.file_name}' and its embeddings deleted."} 