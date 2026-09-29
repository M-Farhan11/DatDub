"""Built-in templates."""

from fastapi import APIRouter

from app.core.exceptions import NotFound
from app.schemas import DatasetSchema, TemplateSummary
from app.templates import get_template, list_templates

router = APIRouter(tags=["templates"])


@router.get("/templates", response_model=list[TemplateSummary])
def templates() -> list[TemplateSummary]:
    return list_templates()


@router.get("/templates/{template_id}", response_model=DatasetSchema)
def template(template_id: str) -> DatasetSchema:
    schema = get_template(template_id)
    if schema is None:
        raise NotFound(f"Unknown template '{template_id}'", code="template_not_found")
    return schema
