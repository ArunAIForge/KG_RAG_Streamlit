# extraction/schemas.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    SCHEME = "Scheme"
    DEPARTMENT = "Department"
    ORGANISATION = "Organisation"
    BENEFICIARY = "BeneficiaryGroup"
    BENEFIT = "Benefit"
    ELIGIBILITY = "EligibilityCriteria"
    PROCEDURE = "ApplicationStep"
    SPONSOR = "Sponsor"


class RelationType(str, Enum):
    ADMINISTERED_BY = "ADMINISTERED_BY"
    MANAGED_BY = "MANAGED_BY"
    SPONSORED_BY = "SPONSORED_BY"
    TARGETS_BENEFICIARY = "TARGETS_BENEFICIARY"
    PROVIDES_BENEFIT = "PROVIDES_BENEFIT"
    REQUIRES_ELIGIBILITY = "REQUIRES_ELIGIBILITY"
    FOLLOWS_PROCEDURE = "FOLLOWS_PROCEDURE"


class NodeEntity(BaseModel):
    id: str = Field(description="Unique deterministic ID (e.g., SCHEME_TN_AGRI_001, DEPT_AGRI)")
    name: str = Field(description="Standardized name of the entity")
    label: EntityType = Field(description="Entity label/type")
    properties: dict = Field(default_factory=dict, description="Additional metadata properties")


class RelationshipTriple(BaseModel):
    source_id: str = Field(description="ID of the source entity node")
    target_id: str = Field(description="ID of the target entity node")
    relation_type: RelationType = Field(description="Type of directed relationship")
    properties: dict = Field(default_factory=dict, description="Metadata on the edge (e.g., funding_percentage)")


class SchemeKnowledgeGraph(BaseModel):
    """Container holding all extracted entities and relationships for one or more schemes."""
    nodes: List[NodeEntity] = Field(default_factory=list, description="Extracted nodes")
    relationships: List[RelationshipTriple] = Field(default_factory=list, description="Extracted edges")