"""Shared display contract for the nine RTLDI levers."""

from __future__ import annotations

from typing import Any, Dict


LEVER_DISPLAY: Dict[int, Dict[str, str]] = {
    1: {
        "name": "Legal Protections",
        "short": "Legal protections",
        "description": "Ordinary law applies consistently to state agents and everyone else.",
        "long_description": "Present when ordinary law is applied consistently to state agents as well as everyone else. Absent when power can act without predictable legal constraint. Multiplies GDP by lowering the risk of arbitrary loss; people and businesses invest and trade more when they know the rules will be enforced fairly. Annual cost is low.",
    },
    2: {
        "name": "Independent Judiciary",
        "short": "Independent judiciary",
        "description": "Courts can uphold right-to-life laws, including against the state.",
        "long_description": "Present when there is a judiciary capable of upholding right-to-life laws even against the state. These protections represent opportunities for property rights and contracts to support reliable capital flows to productive uses. Annual cost is low relative to the scale unlocked.",
    },
    3: {
        "name": "Law Enforcement Accountability",
        "short": "Law enforcement accountability",
        "description": "Law enforcement agencies are accountable for unlawful killings and violence.",
        "long_description": "Present when law enforcement agencies are accountable for unlawful killings and violence. These protections represent opportunities to support greater economic scale by reducing arbitrary risk that can deter investment, labor mobility, and everyday economic activity. Annual cost is primarily institutional oversight.",
    },
    4: {
        "name": "Protection Against Arbitrary Detention",
        "short": "Arbitrary detention protection",
        "description": "Arbitrary detention is prohibited with real legal recourse.",
        "long_description": "Present when arbitrary detention is prohibited with real legal recourse. These protections represent opportunities for individuals and families to plan, work, and invest with greater security, supporting scale in the economy. Annual cost is low.",
    },
    5: {
        "name": "Freedom from Torture and Inhumane Treatment",
        "short": "Freedom from torture",
        "description": "Measures are in place to prevent torture and inhumane treatment.",
        "long_description": "Present when the state has effective measures to prevent torture. These protections represent opportunities to support human capital and cooperation. Annual cost is institutional and training: an investment toward realizing greater scale.",
    },
    6: {
        "name": "Civilian Protection in Conflict Zones",
        "short": "Civilian protection in conflict",
        "description": "Mechanisms protect civilians during conflict.",
        "long_description": "Present when mechanisms exist to protect civilians during conflict. These protections represent opportunities to preserve the productive capacity and future of entire regions. Annual cost is primarily military discipline and rules of engagement.",
    },
    7: {
        "name": "Access to Justice",
        "short": "Access to justice",
        "description": "Ordinary people can bring serious claims and have them heard fairly.",
        "long_description": "Present when ordinary people can bring serious claims and have them heard fairly. These conditions represent opportunities for contracts and rights to function for a wider share of the population. Annual cost is court capacity and legal aid.",
    },
    8: {
        "name": "Freedom of Expression and Whistleblower Protections",
        "short": "Expression and whistleblowers",
        "description": "Expression and whistleblower rights are protected from retaliation.",
        "long_description": "Present when laws protect people who report corruption from retaliation. These conditions represent opportunities for information to flow more accurately and for public resources to be used more effectively. Annual cost is low: mainly passing and enforcing the law.",
    },
    9: {
        "name": "Socioeconomic Conditions",
        "short": "Basic human security",
        "description": "A minimum floor against extreme deprivation is maintained.",
        "long_description": "Present when a society makes the deliberate choice to maintain a minimum floor against extreme deprivation. This reflects political will rather than just economic outcomes. When present, it increases the share of the population able to participate productively, expanding overall economic scale. Annual cost is a political decision about minimum security standards.",
    },
}


def lever_name(num: Any, fallback: str = "") -> str:
    try:
        idx = int(num)
    except (TypeError, ValueError):
        return fallback
    return LEVER_DISPLAY.get(idx, {}).get("name", fallback or f"Lever {idx}")


def lever_short(num: Any, fallback: str = "") -> str:
    try:
        idx = int(num)
    except (TypeError, ValueError):
        return fallback
    return LEVER_DISPLAY.get(idx, {}).get("short", fallback or f"Lever {idx}")


def lever_description(num: Any, fallback: str = "") -> str:
    try:
        idx = int(num)
    except (TypeError, ValueError):
        return fallback
    return LEVER_DISPLAY.get(idx, {}).get("description", fallback)


def lever_long_description(num: Any, fallback: str = "") -> str:
    try:
        idx = int(num)
    except (TypeError, ValueError):
        return fallback
    return LEVER_DISPLAY.get(idx, {}).get("long_description", fallback or lever_description(idx))


def format_compact_usd(value: Any) -> str:
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        n = 0.0
    if abs(n) >= 1e12:
        return f"${n / 1e12:,.2f}T"
    if abs(n) >= 1e9:
        return f"${n / 1e9:,.1f}B"
    if abs(n) >= 1e6:
        return f"${n / 1e6:,.1f}M"
    return f"${n:,.0f}"
