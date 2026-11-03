"""App-owned structured edits. No provider evidence or new budget amount."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from backend.models import ContractModel

class Choice(ContractModel):
    occurrence: int = Field(strict=True,ge=0,le=4)
    placeId: str = Field(min_length=1,max_length=200)

class DwellAnswer(ContractModel):
    occurrence: int = Field(strict=True,ge=0,lt=4)
    minutes: int = Field(strict=True,ge=0,le=10080)
    relation: Literal['exact','minimum','maximum','under','approximate'] = 'approximate'
    zeroCountedTime: bool = Field(default=False,strict=True)
    @model_validator(mode='after')
    def valid(self):
        if self.relation=='under' and self.minutes==0:raise ValueError('A visit cannot take strictly less than zero minutes.')
        return self

class AdvancedEdits(ContractModel):
    dwell: list[DwellAnswer] = Field(default_factory=list,max_length=4)
    budgetScope: Literal['outing','travel'] | None = None
    resetDwell: list[Annotated[int, Field(strict=True,ge=0,lt=4)]] = Field(default_factory=list,max_length=4)
    resetDeparture: bool = Field(default=False,strict=True)
    departure: str | None = Field(default=None,pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    choices: list[Choice] = Field(default_factory=list,max_length=5)
    @model_validator(mode='after')
    def unique(self):
        if any(type(n) is not int or not 0<=n<4 for n in self.resetDwell) or len(set(self.resetDwell))!=len(self.resetDwell) or set(self.resetDwell)&{d.occurrence for d in self.dwell}:raise ValueError('Reset or edit each visit once.')
        if self.resetDeparture and self.departure is not None:raise ValueError('Choose a departure or reset it.')
        if len({d.occurrence for d in self.dwell})!=len(self.dwell) or len({c.occurrence for c in self.choices})!=len(self.choices):
            raise ValueError('Edit each occurrence once.')
        return self
