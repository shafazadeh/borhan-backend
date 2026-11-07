from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Category(str, Enum):
    financial = "financial"
    penalty_compensation = "penalty_compensation"
    intellectual_property = "intellectual_property"
    confidentiality = "confidentiality"
    termination = "termination"
    scope_delivery = "scope_delivery"
    warranty_support = "warranty_support"
    dispute_resolution = "dispute_resolution"
    force_majeure = "force_majeure"
    general_legal = "general_legal"
    non_compete = "non_compete"
    sla_obligations = "sla_obligations"


class ClassificationSource(str, Enum):
    rule_based = "rule_based"
    llm = "llm"


class ClauseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clause_id: str = Field(min_length=1, max_length=128)
    index: int = Field(ge=1)
    article_title: str = Field(default="", max_length=1000)
    text: str = Field(min_length=1, max_length=100000)


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clause_id: str
    primary_category: Category
    secondary_categories: list[Category] = Field(default_factory=list, max_length=11)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    matched_keywords: list[str] = Field(default_factory=list, max_length=100)
    source: ClassificationSource
    degraded: bool = False

    @model_validator(mode="after")
    def unique_categories(self):
        if self.primary_category in self.secondary_categories or len(set(self.secondary_categories)) != len(self.secondary_categories):
            raise ValueError("Categories must be distinct")
        return self
