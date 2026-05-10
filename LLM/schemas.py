from pydantic import BaseModel, Field
from typing import Optional


class WordChunkInput(BaseModel):
    """Input schema for a single Word chunk."""
    title: str = Field(..., description="Section title from the Word document")
    content: str = Field(..., description="Section content text")
    level: int = Field(..., description="Heading level (1 for H1, 2 for H2, etc.)")


class Chunk1Output(BaseModel):
    """Output schema for chunk1 (项目介绍+引导案例).

    This data is shared across all task JSONs as the common "introduction" section.
    """
    project_name: str = Field(..., description="项目名称，从【标题1】提取")
    introduction_case: str = Field(..., description="引导案例完整内容")
    guiding_problem1: str = Field(..., description="引导思考问题1，从案例提炼")
    guiding_problem2: str = Field(..., description="引导思考问题2")
    guiding_problem3: str = Field(..., description="引导思考问题3")


class TaskOutput(BaseModel):
    """Output schema for a single task JSON (chunk2-4).

    Each task JSON contains all fields for one task section.
    """
    cover: dict = Field(..., description="Cover: project_name, task_num, task_name")
    introduction: dict = Field(..., description="Introduction: introduction_case")
    thinking: dict = Field(..., description="Thinking: guiding_problem1-3")
    start: dict = Field(..., description="Start: task_num, task_name")
    catalog_one: dict = Field(..., description="Catalog 1: task_num, task_name")
    catalog_two: dict = Field(..., description="Catalog 2: task_num, task_name")
    catalog_three: dict = Field(..., description="Catalog 3: task_num, task_name")
    catalog_four: dict = Field(..., description="Catalog 4: task_num, task_name")
    catalog_five: dict = Field(..., description="Catalog 5: task_num, task_name")
    catalog_six: dict = Field(..., description="Catalog 6: task_num, task_name")
    description: dict = Field(..., description="Description: task_description, task_requirements1-5")
    target: dict = Field(..., description="Target: task_target1-4, task_focus, task_difficulty")
    summary: dict = Field(..., description="Summary: task_summary")
    key_difficulties_summary: dict = Field(..., description="Key difficulties: key_summary1-3, difficulties_summary1-3")
    expansion: dict = Field(..., description="Expansion: skill_practice, solving_ideas")


class LLMResponse(BaseModel):
    """Generic LLM response wrapper."""
    content: str = Field(..., description="Raw text response from LLM")
    reasoning_details: Optional[str] = Field(None, description="Reasoning content if reasoning_split=True")
