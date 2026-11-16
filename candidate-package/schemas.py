#schemas.py

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationInfo, model_validator


class Classification(str, Enum):
    RFQ = "rfq"
    RFQ_REVISION = "rfq_revision"
    PURCHASE_ORDER = "purchase_order"
    VENDOR_QUOTE = "vendor_quote"
    STATUS_INQUIRY = "status_inquiry"
    AUTO_REPLY = "auto_reply"
    OTHER = "other"


class Unit(str, Enum):
    EA = "EA"
    FT = "FT"
    M = "M"
    IN = "IN"
    BX = "BX"
    PK = "PK"
    PR = "PR"
    DZ = "DZ"
    RL = "RL"
    LB = "LB"
    SET = "SET"
    GAL = "GAL"
    BAG = "BAG"
    CS = "CS"


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str = Field(min_length=1)
    description: str = Field(min_length=1)
    qty: int | float | None
    uom: Unit | None
    source: str = Field(min_length=1)


REVIEWABLE_CLASSIFICATIONS = {
    Classification.RFQ,
    Classification.RFQ_REVISION,
    Classification.PURCHASE_ORDER
}


class EmailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: Classification
    revises: str | None
    duplicate_of: str | None
    needs_review: bool
    review_reason: str | None
    line_items: list[LineItem]

    @model_validator(mode="after")
    def apply_review_policy(self, info: ValidationInfo):
        attachment_failures = (info.context or {}).get("attachment_failures") or []

        if self.classification not in REVIEWABLE_CLASSIFICATIONS:
            self.needs_review = False
            self.review_reason = None
            self.line_items = []
            return self

        if attachment_failures and not self.needs_review:
            self.needs_review = True
            self.review_reason = "Could not read attachment(s): " + ", ".join(attachment_failures)

        if self.needs_review and not self.review_reason:
            self.review_reason = "Flagged for human review."

        if not self.needs_review:
            self.review_reason = None

        return self


def validate_email_result(data, attachment_failures=None):
    context = {"attachment_failures": attachment_failures or []}
    validated = EmailResult.model_validate(data, context=context)

    return validated.model_dump(mode="json")


class ParsedOutput(RootModel[dict[str, EmailResult]]):
    pass