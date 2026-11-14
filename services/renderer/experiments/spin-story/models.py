"""Bounded local authoring input; narration is data, never executable scene code."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCENES=('hook', 'above', 'isolated', 'inward', 'faster', 'outward', 'double', 'energy', 'brake', 'outro')
Coordinate=Annotated[float,Field(ge=-80,le=80,allow_inf_nan=False)]
Vector=tuple[Coordinate,Coordinate,Coordinate]

class ClosedModel(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Voice(ClosedModel):
    name: Annotated[str,StringConstraints(min_length=1,max_length=60)]
    id: Annotated[str,StringConstraints(pattern=r'^[A-Za-z0-9_-]{1,100}$')]

class Beat(ClosedModel):
    scene: Literal['hook','above','isolated','inward','faster','outward','double','energy','brake','outro']
    text: Annotated[str,StringConstraints(min_length=1,max_length=260)]
    camera: tuple[Vector,Vector]
    target: Vector
    pause: Annotated[float,Field(ge=.1,le=1,allow_inf_nan=False)]

class Story(ClosedModel):
    id: Literal['spinning-chair']
    title: Annotated[str,StringConstraints(min_length=1,max_length=120)]
    template: Literal['cartoon-angular-momentum-v1']
    voice: Voice
    objective: Annotated[str,StringConstraints(min_length=20,max_length=1000)]
    sources: Annotated[list[Annotated[str,StringConstraints(pattern=r'^https://',max_length=500)]],Field(min_length=1,max_length=8)]
    beats: Annotated[list[Beat],Field(min_length=10,max_length=10)]

    @model_validator(mode='after')
    def bounded_story(self):
        if tuple(b.scene for b in self.beats)!=SCENES:
            raise ValueError('This action adapter requires the documented scene order')
        words=sum(len(b.text.split()) for b in self.beats)
        if not 85<=words<=160:
            raise ValueError('Narration must be 85–160 words before synthesis')
        return self
