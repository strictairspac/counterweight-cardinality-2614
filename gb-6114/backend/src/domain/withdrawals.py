"""Pure matching rules for withdrawn measurement-basis pairs."""

from collections.abc import Mapping


MASS_KEYS = (
    "mass", "mass_band", "massBand", "weight", "weight_band", "weightBand",
    "weight_tier", "weightTier", "weightClass",
    "重量档", "重量档位",
)
SLOT_KEYS = (
    "slot", "slot_band", "slotBand", "slot_width", "slotWidth",
    "slot_width_band", "slotWidthBand", "slot_tier", "slotTier",
    "slot_width_tier", "slotWidthTier",
    "槽宽档", "槽宽档位",
)
PAIR_KEYS = ("pair", "bands", "tier_pair", "档位对", "withdrawn_pair")
CODE_KEYS = ("code", "check_code", "checkCode", "query_code", "复检号", "查询编号")


def _as_pair(value):
    if isinstance(value, Mapping):
        mass = next((value.get(key) for key in MASS_KEYS if isinstance(value.get(key), str)), None)
        slot = next((value.get(key) for key in SLOT_KEYS if isinstance(value.get(key), str)), None)
        if mass is not None and slot is not None:
            return mass, slot
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(item, str) for item in value):
        return value[0], value[1]
    return None


METADATA_KEYS = {
    "withdrawal", "withdrawals", "withdrawn_bases", "withdrawn_pairs",
    "revoked_pairs", "revocations", "validity", "validity_status",
    "certificate_status", "certificate_state", "evidence_status",
}


def queried_pairs(result):
    """Return every mass/slot pair represented by a certificate result.

    The actual COUNT value is deliberately irrelevant: a query that verified
    zero pieces still queried the pair and is therefore affected.
    """
    pairs = set()

    def visit(value):
        pair = _as_pair(value)
        if pair is not None:
            pairs.add(pair)
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key not in METADATA_KEYS:
                    visit(child)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                visit(child)

    visit(result)
    return pairs


def queried_codes(result):
    """Collect check codes for certificates that store codes instead of bands."""
    codes = set()

    def visit(value):
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in CODE_KEYS and isinstance(child, str):
                    codes.add(child)
                else:
                    visit(child)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                visit(child)

    visit(result)
    return codes


def pairs_from_case_codes(case_payload, codes):
    if not isinstance(case_payload, Mapping):
        return set()
    checks = case_payload.get("checks")
    if not isinstance(checks, list):
        return set()
    pairs = set()
    for check in checks:
        if not isinstance(check, Mapping) or check.get("code") not in codes:
            continue
        pair = _as_pair(check)
        if pair is not None:
            pairs.add(pair)
    return pairs


def withdrawal_pair(withdrawal):
    if isinstance(withdrawal, Mapping):
        return withdrawal.get("mass"), withdrawal.get("slot")
    return withdrawal.mass, withdrawal.slot


def matching_withdrawals(result, withdrawals):
    queried = queried_pairs(result)
    return [
        withdrawal for withdrawal in withdrawals
        if tuple(withdrawal_pair(withdrawal)) in queried
    ]


def is_withdrawn(result, withdrawals):
    return bool(matching_withdrawals(result, withdrawals))


# Vocabulary aliases.
is_revoked = is_withdrawn
is_invalid = is_withdrawn
has_withdrawn_basis = is_withdrawn
certificate_is_invalid = is_withdrawn
find_matching_withdrawals = matching_withdrawals


def pair_dicts(pairs):
    return [{"mass": mass, "slot": slot} for mass, slot in sorted(pairs)]
