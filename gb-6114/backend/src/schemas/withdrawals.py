from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.inputs import label

MASS_KEYS = (
    "mass", "mass_band", "massBand", "weight", "weight_band", "weightBand",
    "weight_tier", "weightTier", "weight_class", "重量档", "重量档位",
)
SLOT_KEYS = (
    "slot", "slot_band", "slotBand", "slot_width", "slotWidth",
    "slot_width_band", "slotWidthBand", "slot_tier", "slotTier",
    "slot_width_tier", "slotWidthTier", "槽宽档", "槽宽档位",
)
REASON_KEYS = ("reason", "note", "comment", "basis_reason", "basisReason", "原因", "说明")
CASE_KEYS = ("case_id", "caseId", "case", "id", "资料编号")


def _first(data, keys):
    return next((data[key] for key in keys if key in data and data[key] is not None), None)


class WithdrawalInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    case_id: int | None = None
    mass: str | None = None
    slot: str | None = None
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        result = dict(data)

        pair = _first(result, ("pair", "bands", "tier_pair", "tierPair", "档位对", "withdrawn_pair", "withdrawnPair"))
        if isinstance(pair, dict):
            result.setdefault("mass", _first(pair, MASS_KEYS))
            result.setdefault("slot", _first(pair, SLOT_KEYS))
        elif isinstance(pair, (list, tuple)) and len(pair) == 2:
            result.setdefault("mass", pair[0])
            result.setdefault("slot", pair[1])

        result.setdefault("mass", _first(result, MASS_KEYS))
        result.setdefault("slot", _first(result, SLOT_KEYS))
        result.setdefault("reason", _first(result, REASON_KEYS) or "")
        result.setdefault("case_id", _first(result, CASE_KEYS))
        return result

    @model_validator(mode="after")
    def validate_labels(self):
        if self.mass is None or self.slot is None:
            raise ValueError("必须提供重量档 mass 和槽宽档 slot")
        self.mass = label(self.mass)
        self.slot = label(self.slot)
        if not isinstance(self.reason, str):
            raise ValueError("撤回原因必须是字符串")
        self.reason = self.reason.strip()
        return self
