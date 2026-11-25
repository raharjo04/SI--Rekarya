import html
import re

import streamlit as st


NAVY = "#1E3A8A"
TEAL = "#0D9488"
CORAL = "#DC2626"
AMBER = "#D97706"
SLATE = "#1E293B"
MUTED = "#64748B"
PERSONA_COLORS = {
    "Disengaged": "#B45309",
    "High Burnout": "#DC2626",
    "Senior Veteran": "#1E3A8A",
    "Engaged Stars": "#0D9488",
}


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --si-navy: #1E3A8A;
            --si-teal: #0D9488;
            --si-coral: #DC2626;
            --si-amber: #D97706;
            --si-bg: #F8FAFC;
            --si-card: #FFFFFF;
            --si-text: #1E293B;
            --si-muted: #64748B;
            --si-border: #E2E8F0;
            --si-shadow: 0 2px 8px rgba(15, 23, 42, 0.045);
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 16px;
        }
        [data-testid="stAppViewContainer"] {
            background: var(--si-bg);
            color: var(--si-text);
        }
        [data-testid="stHeader"] {
            background: rgba(248, 250, 252, 0.92);
        }
        .main .block-container {
            max-width: 1200px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--si-border);
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }
        h1, h2, h3, h4 {
            color: var(--si-text);
            letter-spacing: -0.025em;
        }
        h1 { font-size: 2rem; }
        h2 { font-size: 1.5rem; }
        h3 { font-size: 1.25rem; }
        p, [data-testid="stMarkdownContainer"] {
            font-size: 16px;
        }
        p, label, [data-testid="stCaptionContainer"] {
            color: var(--si-text);
        }
        [data-testid="stCaptionContainer"] {
            color: var(--si-muted);
            font-size: 14px;
        }
        [data-testid="stCaptionContainer"] p {
            font-size: 14px;
        }
        [data-testid="stSlider"] label,
        [data-testid="stCheckbox"] label,
        [data-testid="stSlider"] [data-testid="stWidgetLabel"] p,
        [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p {
            font-size: 15px;
        }
        [data-testid="stMetric"] {
            background: var(--si-card);
            border: 1px solid var(--si-border);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: var(--si-shadow);
            min-height: 112px;
        }
        [data-testid="stMetricLabel"] {
            color: var(--si-muted) !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            letter-spacing: 0.045em;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--si-navy) !important;
            font-size: 36px !important;
            font-weight: 800 !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--si-border) !important;
            border-radius: 14px !important;
            background: var(--si-card);
            box-shadow: var(--si-shadow);
        }
        [data-testid="stForm"] {
            border: 1px solid var(--si-border);
            border-radius: 14px;
            background: var(--si-card);
            padding: 1.15rem;
        }
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: 9px;
            color: #1E293B;
            font-weight: 700;
            min-height: 2.7rem;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        [data-testid="stFormSubmitButton"] button[kind="primary"],
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stDownloadButton"] button {
            background: var(--si-navy);
            border-color: var(--si-navy);
            color: #FFFFFF !important;
            font-weight: 800;
        }
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stButton"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(30, 58, 138, 0.18);
        }
        [data-testid="stDownloadButton"] button {
            border-radius: 9px;
            border: 1px solid #0F766E;
            color: #FFFFFF !important;
            background: #0F766E;
            font-weight: 800;
            min-height: 2.7rem;
        }
        [data-testid="stDownloadButton"] button:hover {
            background: #115E59;
            color: #FFFFFF;
            border-color: #115E59;
        }
        [data-testid="stFormSubmitButton"] button:focus-visible,
        [data-testid="stButton"] button:focus-visible,
        [data-testid="stDownloadButton"] button:focus-visible {
            outline: 3px solid #F59E0B;
            outline-offset: 2px;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--si-navy);
            border-bottom-color: var(--si-navy);
            font-weight: 700;
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border: 1px solid var(--si-border);
            border-radius: 10px;
            overflow: hidden;
        }
        [data-testid="stAlert"] {
            border-radius: 11px;
        }
        [data-testid="stFileUploader"] section {
            border: 1px dashed #94A3B8;
            border-radius: 12px;
            background: #F8FAFC;
        }
        .si-hero {
            margin: 0.15rem 0 1.2rem;
        }
        .si-hero h1 {
            margin: 0;
            color: var(--si-navy);
            font-size: clamp(1.8rem, 3vw, 2.2rem);
            line-height: 1.2;
        }
        .si-hero p {
            margin: 0.35rem 0 0;
            color: var(--si-muted);
            font-size: 16px;
        }
        .si-brand {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 0.4rem 0.15rem 0.9rem;
        }
        .si-brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 10px;
            background: var(--si-navy);
            color: #FFFFFF;
            font-size: 1.1rem;
            font-weight: 800;
        }
        .si-brand-title {
            color: var(--si-navy);
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .si-brand-caption {
            color: var(--si-muted);
            font-size: 0.72rem;
            line-height: 1.35;
        }
        .si-persona-badge, .si-risk-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            border-radius: 999px;
            padding: 0.42rem 0.8rem;
            font-size: 15px;
            font-weight: 800;
            line-height: 1.2;
        }
        .si-risk-high {
            color: #991B1B;
            background: #FEE2E2;
            border: 1px solid #FCA5A5;
        }
        .si-risk-medium {
            color: #78350F;
            background: #FEF3C7;
            border: 1px solid #FCD34D;
        }
        .si-risk-low {
            color: #1E40AF;
            background: #DBEAFE;
            border: 1px solid #93C5FD;
        }
        .si-risk-neutral {
            color: #334155;
            background: #E2E8F0;
            border: 1px solid #CBD5E1;
        }
        .si-result-card {
            border: 1px solid var(--si-border);
            border-left: 5px solid var(--si-navy);
            border-radius: 14px;
            padding: 1.2rem 1.3rem;
            margin-bottom: 0.85rem;
            background: #FFFFFF;
            box-shadow: var(--si-shadow);
        }
        .si-result-title {
            color: var(--si-text);
            font-size: 1.3rem;
            font-weight: 750;
        }
        .si-result-copy {
            color: var(--si-muted);
            font-size: 16px;
            margin-top: 0.3rem;
        }
        .si-step {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-height: 3.2rem;
            padding: 0.7rem 0.9rem;
            border: 1px solid var(--si-border);
            border-radius: 12px;
            background: #FFFFFF;
            box-shadow: var(--si-shadow);
            color: var(--si-text);
            font-weight: 700;
            font-size: 15px;
        }
        .si-step-active {
            border: 2px solid var(--si-navy);
            background: #EFF6FF;
            color: var(--si-navy);
            box-shadow: 0 3px 12px rgba(30, 58, 138, 0.14);
        }
        .si-step-complete {
            border-color: var(--si-teal);
            background: #F0FDFA;
        }
        .si-step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.8rem;
            height: 1.8rem;
            flex: 0 0 1.8rem;
            border-radius: 50%;
            background: #DBEAFE;
            color: var(--si-navy);
            font-size: 0.85rem;
            font-weight: 800;
        }
        .si-check-card {
            border: 1px solid var(--si-border);
            border-left: 4px solid var(--si-teal);
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin: 0.5rem 0;
            background: #FFFFFF;
            color: var(--si-text);
            box-shadow: var(--si-shadow);
            font-size: 17px;
            line-height: 1.5;
        }
        .si-small-label {
            color: var(--si-muted);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.035em;
            text-transform: uppercase;
        }
        @media (max-width: 720px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            [data-testid="stMetric"] {
                min-height: 98px;
                padding: 0.85rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, icon: str = "📊") -> None:
    del icon
    st.markdown(
        f"""
        <div class="si-hero">
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_branding() -> None:
    st.sidebar.markdown(
        """
        <div class="si-brand">
            <span class="si-brand-mark">S</span>
            <div>
                <div class="si-brand-title">SI-REKARYA</div>
                <div class="si-brand-caption">HR Analytics Dashboard</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        "Analitik retensi dan klasterisasi karyawan berbasis K-Means."
    )


def metric_card(
    label: str,
    value: str,
    icon: str,
    delta: str | None = None,
    help_text: str | None = None,
) -> None:
    st.metric(
        label=f"{icon}  {label}",
        value=value,
        delta=delta,
        help=help_text,
    )


def persona_badge(label: str, color: str) -> None:
    safe_color = color if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) else NAVY

    def linear_channel(value: int) -> float:
        normalized = value / 255
        if normalized <= 0.04045:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = (
        int(safe_color[index : index + 2], 16) for index in (1, 3, 5)
    )
    luminance = (
        0.2126 * linear_channel(red)
        + 0.7152 * linear_channel(green)
        + 0.0722 * linear_channel(blue)
    )
    white_contrast = 1.05 / (luminance + 0.05)
    dark_contrast = (luminance + 0.05) / 0.008
    text_color = "#FFFFFF" if white_contrast >= dark_contrast else "#0F172A"
    st.markdown(
        f'<span class="si-persona-badge" style="background:{safe_color};'
        f'color:{text_color};border:1px solid {safe_color}">'
        f"{html.escape(label)}</span>",
        unsafe_allow_html=True,
    )


def risk_badge(label: str) -> None:
    normalized = label.casefold()
    if "tinggi" in normalized:
        badge_class = "si-risk-high"
    elif "sedang" in normalized:
        badge_class = "si-risk-medium"
    elif "rendah" in normalized:
        badge_class = "si-risk-low"
    else:
        badge_class = "si-risk-neutral"
    st.markdown(
        f'<span class="si-risk-badge {badge_class}">{html.escape(label)}</span>',
        unsafe_allow_html=True,
    )


def recommendation_card(text: str, number: int, rule: str | None = None) -> None:
    rule_label = f'<span class="si-small-label">{html.escape(rule)}</span>' if rule else ""
    st.markdown(
        f'<div class="si-check-card"><strong>{number:02d}</strong> &nbsp;'
        f'{html.escape(text)} {rule_label}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, description: str, icon: str = "🧭") -> None:
    st.markdown(
        f"""
        <div class="si-result-card">
            <div class="si-result-title">{html.escape(icon)} &nbsp;{html.escape(title)}</div>
            <div class="si-result-copy">{html.escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
