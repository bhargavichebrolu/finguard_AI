"""Routes for the summary report and report downloads (PRD 6.1, 6.9)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.reports import SummaryReport
from app.models.enums import UserRole
from app.models.records import User
from app.security.dependencies import DbSession, ServingModelDep, require_permission
from app.security.permissions import Permission
from app.services.report_service import ReportType, build_summary, report_lines

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/summary", response_model=SummaryReport)
def read_summary(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SUMMARY))],
    db: DbSession,
    model: ServingModelDep,
) -> SummaryReport:
    """Return totals for your scope. Flags, statuses and labels are reported separately."""
    return build_summary(db, model, user.role == UserRole.DEMO)


@router.get("/export", responses={200: {"content": {"text/csv": {}}}})
def export_report(
    user: Annotated[User, Depends(require_permission(Permission.EXPORT_REPORTS))],
    model: ServingModelDep,
    report_type: ReportType = "predictions",
) -> StreamingResponse:
    """Download a report as CSV."""
    return StreamingResponse(
        report_lines(report_type, user.role == UserRole.DEMO, model),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="finguard-{report_type}.csv"'},
    )
