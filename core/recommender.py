from collections.abc import Mapping
from numbers import Real
from typing import Any

from core.artifacts import load_artifacts
from core.contracts import RecommendationResult


def _promotion_status(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"", "na", "n/a", "nan", "none"}:
            return None
        if normalized in {"1", "true", "yes", "ya"}:
            return True
        if normalized in {"0", "false", "no", "tidak"}:
            return False
    if isinstance(value, Real):
        if value != value:
            return None
        if value in (0, 1):
            return bool(value)
    raise ValueError(
        "promotion_last_5years harus berupa boolean atau nilai 0/1."
    )


def _risk_for_persona(persona: str) -> str:
    profiles = load_artifacts()["profiles"]["clusters"]
    matching = [
        profile
        for profile in profiles
        if profile["persona"].casefold() == persona.casefold()
    ]
    if not matching:
        raise ValueError(f"Persona '{persona}' tidak ditemukan di profil klaster.")
    if len(matching) > 1:
        raise ValueError(f"Persona '{persona}' muncul lebih dari sekali di profil.")
    return matching[0]["risk_level"]


def recommend(
    persona: str,
    data: Mapping[str, Any],
    risk_level: str | None = None,
) -> RecommendationResult:
    """Return policy-based HR recommendations; these are not model outputs."""
    normalized_persona = persona.casefold()
    recommendations: list[str] = []
    triggered_rules: list[str] = []

    hours_value = data.get("average_montly_hours", data.get("average_monthly_hours"))
    if hours_value is None:
        raise ValueError("Data wajib memiliki kolom jam kerja bulanan.")
    hours = float(hours_value)
    projects = int(data["number_project"])
    evaluation = float(data["last_evaluation"])
    satisfaction = float(data["satisfaction_level"])
    promoted = _promotion_status(data.get("promotion_last_5years"))
    resolved_risk_level = risk_level or _risk_for_persona(persona)

    if "high burnout" in normalized_persona and (hours > 250 or projects >= 6):
        triggered_rules.append("R1")
        recommendations.extend(
            [
                "Redistribusikan proyek dan batasi lembur.",
                "Tawarkan cuti pemulihan.",
                "Tinjau kompensasi dan peluang promosi.",
            ]
        )
    if "disengaged" in normalized_persona and evaluation < 0.60:
        triggered_rules.append("R2")
        recommendations.extend(
            [
                "Jadwalkan sesi coaching 1-on-1.",
                "Lakukan asesmen kecocokan peran (role fit).",
                "Tawarkan program reskilling.",
            ]
        )
    if "engaged stars" in normalized_persona and evaluation >= 0.80:
        triggered_rules.append("R3")
        recommendations.extend(
            [
                "Pertimbangkan jalur leadership fast-track.",
                "Tawarkan insentif retensi.",
                "Tugaskan sebagai mentor.",
            ]
        )
    if "senior veteran" in normalized_persona and promoted is False:
        triggered_rules.append("R4")
        recommendations.extend(
            [
                "Tinjau jenjang jabatan dan tunjangan senioritas.",
                "Pertimbangkan rotasi ke proyek strategis.",
            ]
        )
    if satisfaction < 0.35:
        triggered_rules.append("R5")
        recommendations.append(
            "Peringatan dini: jadwalkan konseling HR dalam 7 hari kerja."
        )

    return {
        "risk_level": resolved_risk_level,
        "recommendations": recommendations,
        "triggered_rules": triggered_rules,
        "policy_note": "Rekomendasi merupakan heuristik kebijakan HR, bukan keluaran model.",
    }
