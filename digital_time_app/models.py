from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Date:
    # This dataclass represents the date object
    _id: str
    title: str
    selected_date: str
    time_delta: str


@dataclass
class User:
    _id: str
    email: str
    password: str
    dates: list[str] = field(default_factory=list)
