from pydantic import BaseModel, Field
from typing import List, Optional

class Cover(BaseModel):
    task_num:str = Field(
        ...,
        description  = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    project_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Introduction(BaseModel):
    introduction_case:str = Field(
        ...,
        max_length = 190,
        description =  {"mode":"summary"}
    )

    # ==========introduction_image==========

class Thinking(BaseModel):
    guiding_problem1:str = Field(
        ...,
        max_length = 30,
        description =  {"mode":"summary"}
    )

    guiding_problem2:str = Field(
        ...,
        max_length = 30,
        description =  {"mode":"summary"}
    )

    guiding_problem3:str = Field(
        ...,
        max_length = 30,
        description =  {"mode":"summary"}
    )

    # ==========thinking_image=========

class Start(BaseModel):
    task_num:str = Field(
        ...,
        description  = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    # ==========start_image==========

class Catalog_one(BaseModel):
    task_num:str = Field(
        ...,
        description  = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Description(BaseModel):
    task_description:str = Field(
        ...,
        max_length = 110,
        description = {"mode":"raw_copy"}
    )

    task_requirements1:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_requirements2:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_requirements3:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_requirements4:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy", "optional": True}
    )

    task_requirements5:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy", "optional": True}
    )

    # ==========description_image==========

class Catalog_two(BaseModel):
    task_num:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Target(BaseModel):
    task_target1:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_target2:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_target3:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_target4:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_focus:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    task_difficulty:str = Field(
        ...,
        max_length = 30,
        description = {"mode":"copy"}
    )

    # ==========target_image==========

class Catalog_three(BaseModel):
    task_num:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Catalog_four(BaseModel):
    task_num:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Catalog_five(BaseModel):
    task_num:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Summary(BaseModel):
    task_summary:str = Field(
        ...,
        max_length = 140,
        description = {"mode":"summary"}
    )

    # ==========summary_image==========

class Key_difficulties_summary(BaseModel):
    key_summary1:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    key_summary2:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    key_summary3:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    difficulties_summary1:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    difficulties_summary2:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    difficulties_summary3:str = Field(
        ...,
        max_length = 20,
        description = {"mode":"summary"}
    )

    # ==========key_difficulties_summary_image==========

class Catalog_six(BaseModel):
    task_num:str = Field(
        ...,
        description = {"mode":"copy"}
    )

    task_name:str = Field(
        ...,
        description = {"mode":"copy"}
    )

class Expansion(BaseModel):
    skill_practice:str = Field(
        ...,
        max_length = 125,
        description = {"mode":"raw_copy"}
    )

    solving_ideas:str = Field(
        ...,
        max_length = 125,
        description = {"mode":"summary"}
    )

    # ==========expansion_image==========
