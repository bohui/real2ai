"""Geographical and location enums."""

from enum import Enum


class AustralianState(str, Enum):
    """Australian states and territories"""
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    NT = "NT"
    ACT = "ACT"
