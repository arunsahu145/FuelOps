"""
Petrol Pump Finance Manager ERP — Backup API
Handles database backup creation, listing, deletion, export, and restore.
Uses SQLite's built-in backup API for safe, consistent copies.
"""
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import DB_PATH, BASE_DIR
from database import engine as db_engine_module

router = APIRouter(prefix="/api/backup")

BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


class RestoreRequest(BaseModel):
    filename: str


def _get_backup_meta(filepath: Path) -> dict:
    """Extract metadata for a single backup file."""
    stat = filepath.stat()
    size_mb = stat.st_size / (1024 * 1024)
    created = datetime.fromtimestamp(stat.st_mtime)
    return {
        "filename": filepath.name,
        "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
        "created_timestamp": stat.st_mtime,
        "size_mb": round(size_mb, 2),
        "size_display": f"{size_mb:.2f} MB" if size_mb >= 1 else f"{stat.st_size / 1024:.1f} KB",
    }


@router.post("/create")
def create_backup():
    """
    Create a ZIP backup of petrol_pump.db using SQLite's online backup API.
    This safely handles WAL mode by consolidating all data into a single clean copy.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"fuelops_backup_{timestamp}.zip"
    zip_path = BACKUP_DIR / backup_filename

    # Create a temporary consolidated copy using sqlite3 backup API
    temp_db_path = BACKUP_DIR / f"_temp_backup_{timestamp}.db"

    try:
        # Connect to the live database and create a clean backup
        source_conn = sqlite3.connect(str(DB_PATH))
        dest_conn = sqlite3.connect(str(temp_db_path))
        source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        # Compress into ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_db_path, "petrol_pump.db")

    except Exception as e:
        # Clean up on failure
        if zip_path.exists():
            zip_path.unlink()
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")
    finally:
        # Always clean up temp file
        if temp_db_path.exists():
            temp_db_path.unlink()

    meta = _get_backup_meta(zip_path)
    return {
        "success": True,
        "message": f"Backup created: {backup_filename}",
        "backup": meta,
    }


@router.get("/list")
def list_backups():
    """List all backup ZIP files in the backups directory, sorted newest first."""
    backups = []
    for f in sorted(BACKUP_DIR.glob("fuelops_backup_*.zip"), reverse=True):
        backups.append(_get_backup_meta(f))

    # Determine last backup info for status card
    last_backup_time = None
    if backups:
        last_backup_time = backups[0]["created_at"]

    return {
        "backups": backups,
        "total_count": len(backups),
        "last_backup_time": last_backup_time,
    }


@router.delete("/{filename}")
def delete_backup(filename: str):
    """Delete a specific backup file."""
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    if not filepath.name.startswith("fuelops_backup_"):
        raise HTTPException(status_code=400, detail="Invalid backup file")

    filepath.unlink()
    return {"success": True, "message": f"Deleted {filename}"}


@router.post("/restore")
def restore_backup(req: RestoreRequest):
    """
    Restore the database from a backup ZIP file.
    Safety procedure:
    1. Dispose all SQLAlchemy connections
    2. Create a rollback copy (.bak) of current DB
    3. Clean WAL/SHM files
    4. Extract and overwrite the database
    5. Re-initialize the engine
    """
    filepath = BACKUP_DIR / req.filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    # Validate the ZIP contains petrol_pump.db
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            if "petrol_pump.db" not in zf.namelist():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backup: ZIP does not contain petrol_pump.db"
                )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Corrupted backup file")

    bak_path = DB_PATH.parent / "petrol_pump.db.bak"
    wal_path = DB_PATH.parent / "petrol_pump.db-wal"
    shm_path = DB_PATH.parent / "petrol_pump.db-shm"

    try:
        # Step 1: Dispose all active connections
        db_engine_module.engine.dispose()

        # Step 2: Create rollback safety copy
        if DB_PATH.exists():
            shutil.copy2(str(DB_PATH), str(bak_path))

        # Step 3: Remove WAL and SHM files
        for log_file in [wal_path, shm_path]:
            if log_file.exists():
                log_file.unlink()

        # Step 4: Extract and overwrite
        with zipfile.ZipFile(filepath, 'r') as zf:
            zf.extract("petrol_pump.db", path=str(DB_PATH.parent))

        # Step 5: Re-create the engine and session factory
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker
        from config import DATABASE_URL

        new_engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False,
            pool_pre_ping=True,
        )

        @event.listens_for(new_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        db_engine_module.engine = new_engine
        db_engine_module.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=new_engine
        )

        # Clean up rollback file on success
        if bak_path.exists():
            bak_path.unlink()

        return {
            "success": True,
            "message": f"Database restored from {req.filename}. Application data has been refreshed.",
        }

    except HTTPException:
        raise
    except Exception as e:
        # Attempt rollback
        try:
            if bak_path.exists():
                shutil.copy2(str(bak_path), str(DB_PATH))
                # Re-initialize engine after rollback
                from sqlalchemy import create_engine, event
                from sqlalchemy.orm import sessionmaker
                from config import DATABASE_URL

                rollback_engine = create_engine(
                    DATABASE_URL,
                    connect_args={"check_same_thread": False},
                    echo=False, pool_pre_ping=True,
                )

                @event.listens_for(rollback_engine, "connect")
                def set_sqlite_pragma_rb(dbapi_conn, conn_rec):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()

                db_engine_module.engine = rollback_engine
                db_engine_module.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=rollback_engine
                )
        except Exception:
            pass  # Last resort — manual intervention needed

        raise HTTPException(
            status_code=500,
            detail=f"Restore failed (rollback attempted): {str(e)}"
        )


@router.get("/export/{filename}")
def get_export_path(filename: str):
    """Return the full filesystem path of a backup file for the UI to copy."""
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    return {
        "filepath": str(filepath),
        "filename": filename,
        "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
    }
