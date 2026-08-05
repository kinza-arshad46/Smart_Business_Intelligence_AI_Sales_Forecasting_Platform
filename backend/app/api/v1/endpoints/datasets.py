import json
import os
import uuid
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.dataset import Dataset, DatasetStatus
from app.models.sales import SalesRecord
from app.models.user import User
from app.schemas.dataset import DatasetOut, DatasetValidationReport
from app.services.activity_service import log_activity
from app.services.data_processing import read_upload_file, validate_and_clean, dataframe_to_records

router = APIRouter(prefix="/datasets", tags=["Data Management"])


@router.post("/upload", response_model=DatasetOut)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.ALLOWED_UPLOAD_EXTENSIONS}",
        )

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.1f} MB). "
                                                      f"Limit is {settings.MAX_UPLOAD_SIZE_MB} MB.")

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    stored_path = Path(settings.UPLOAD_DIR) / stored_filename
    with open(stored_path, "wb") as f:
        f.write(contents)

    dataset = Dataset(
        owner_id=current_user.id,
        filename=stored_filename,
        original_filename=file.filename,
        file_path=str(stored_path),
        status=DatasetStatus.VALIDATING,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # --- Validate & clean ---
    try:
        raw_df = read_upload_file(str(stored_path))
    except Exception as e:
        dataset.status = DatasetStatus.INVALID
        dataset.validation_report = json.dumps({"errors": [f"Could not read file: {e}"]})
        db.commit()
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    clean_df, report = validate_and_clean(raw_df)
    dataset.validation_report = json.dumps(report)

    if not report["is_valid"]:
        dataset.status = DatasetStatus.INVALID
        db.commit()
        raise HTTPException(status_code=422, detail=report)

    # --- Persist rows ---
    records = dataframe_to_records(clean_df, dataset.id)
    db.bulk_insert_mappings(SalesRecord, records)
    dataset.row_count = len(records)
    dataset.status = DatasetStatus.PROCESSED
    db.commit()
    db.refresh(dataset)

    log_activity(db, current_user.id, "dataset_upload",
                 {"dataset_id": dataset.id, "rows": dataset.row_count},
                 request.client.host if request.client else None)

    return dataset


@router.get("", response_model=List[DatasetOut])
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Dataset)
    if current_user.role.value != "admin":
        q = q.filter(Dataset.owner_id == current_user.id)
    return q.order_by(Dataset.uploaded_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    return dataset


@router.get("/{dataset_id}/validation-report", response_model=DatasetValidationReport)
def get_validation_report(dataset_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    return json.loads(dataset.validation_report or "{}")


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    if os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)
    db.delete(dataset)
    db.commit()
    return {"detail": "Dataset deleted"}


def _get_owned_dataset(db: Session, dataset_id: int, current_user: User) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if current_user.role.value != "admin" and dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
    return dataset
