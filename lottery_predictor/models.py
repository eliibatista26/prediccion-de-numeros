from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class LotteryResult:
    lottery: str
    draw: str
    draw_date: date
    numbers: tuple[int, ...]
    source: str

    @property
    def key(self) -> str:
        numbers = "-".join(f"{number:02d}" for number in self.numbers)
        return f"{self.draw_date.isoformat()}|{self.lottery}|{self.draw}|{numbers}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["draw_date"] = self.draw_date.isoformat()
        data["numbers"] = list(self.numbers)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LotteryResult":
        return cls(
            lottery=str(data["lottery"]),
            draw=str(data.get("draw") or "General"),
            draw_date=datetime.strptime(str(data["draw_date"]), "%Y-%m-%d").date(),
            numbers=tuple(int(number) for number in data["numbers"]),
            source=str(data.get("source") or "unknown"),
        )

