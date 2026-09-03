import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import Analysis, LogEntry
from app.services.parser import parse_log_file
from app.services import analyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["analyses"])
templates = Jinja2Templates(directory="app/templates")


def _run_analysis(analysis_id: str, filename: str, lines: list[str]) -> None:
    """Background task: classify log lines, generate summary, and update the DB record."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis is None:
            logger.error("Background task could not find analysis %s", analysis_id)
            return

        analysis.status = "running"
        db.commit()

        # classify_entries returns list[dict] with keys: line_number, classification, reason
        classified = analyzer.classify_entries(lines)

        # Reconstruct original content by line number (classify_entries does not return content)
        line_map = {i + 1: lines[i] for i in range(len(lines))}

        entries: list[LogEntry] = []
        normal = suspicious = critical = 0
        critical_lines: list[str] = []

        for item in classified:
            line_num = item["line_number"]
            cls = item["classification"]
            reason = item["reason"]
            content = line_map.get(line_num, "")

            if cls == "normal":
                normal += 1
            elif cls == "suspicious":
                suspicious += 1
            elif cls == "critical":
                critical += 1
                critical_lines.append(content)

            entries.append(
                LogEntry(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    line_number=line_num,
                    content=content,
                    classification=cls,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                )
            )

        db.bulk_save_objects(entries)

        summary = analyzer.generate_summary(
            filename=filename,
            normal=normal,
            suspicious=suspicious,
            critical=critical,
            critical_entries=critical_lines,
        )

        analysis.total_lines = len(lines)
        analysis.normal_count = normal
        analysis.suspicious_count = suspicious
        analysis.critical_count = critical
        analysis.summary = summary
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception:
        logger.exception("Analysis %s failed", analysis_id)
        try:
            analysis.status = "failed"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/", status_code=303)
async def create_analysis(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept a log file upload, persist a pending record, schedule AI analysis as a
    background task, and immediately redirect the browser to the result page."""
    raw_bytes = await file.read()
    if len(raw_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File must be UTF-8 encoded text.")

    lines = parse_log_file(content)

    analysis_id = str(uuid.uuid4())
    analysis = Analysis(
        id=analysis_id,
        filename=file.filename or "upload.log",
        status="pending",
        total_lines=len(lines),
        created_at=datetime.now(timezone.utc),
    )
    db.add(analysis)
    db.commit()

    if lines:
        background_tasks.add_task(_run_analysis, analysis_id, analysis.filename, lines)
    else:
        # Nothing to classify — mark complete immediately without a background task
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()

    return RedirectResponse(url=f"/analyses/{analysis_id}", status_code=303)


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, request: Request, db: Session = Depends(get_db)):
    """Return the analysis result page. Status reflects live DB state
    (pending / running / completed / failed); the template renders each state."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    entries = (
        db.query(LogEntry)
        .filter(LogEntry.analysis_id == analysis_id)
        .order_by(LogEntry.line_number)
        .all()
    )

    return templates.TemplateResponse(
        "analysis.html",
        {"request": request, "analysis": analysis, "entries": entries},
    )
