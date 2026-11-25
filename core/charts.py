from collections.abc import Mapping
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from core.config import FEATURE_LABELS, FEATURES
from core.contracts import ClusterProfile, PredictionResult
from core.ui_theme import PERSONA_COLORS

NAVY = "#1E3A8A"
TEAL = "#0D9488"
CORAL = "#DC2626"
PLOT_FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
PERSONA_SYMBOLS = ["circle", "square", "triangle-up", "diamond"]


def _format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _apply_plot_theme(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT, color="#1E293B", size=13),
        title=dict(x=0.01, xanchor="left", font=dict(size=18, color=NAVY)),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(size=13),
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#CBD5E1",
            font=dict(family=PLOT_FONT, color="#1E293B", size=13),
        ),
        margin=dict(t=55, l=45, r=35, b=70),
        height=420,
        separators=",.",
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        zeroline=False,
        linecolor="#CBD5E1",
        tickfont=dict(color="#334155", size=13),
        title_font=dict(size=14),
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        zeroline=False,
        linecolor="#CBD5E1",
        tickfont=dict(color="#334155", size=13),
        title_font=dict(size=14),
    )
    return figure


def summary_scatter(dataframe: pd.DataFrame) -> go.Figure:
    frame = dataframe.sample(n=min(1500, len(dataframe)), random_state=42).copy()
    frame["Status"] = frame["left"].map({0: "Masih bekerja", 1: "Keluar"})
    figure = px.scatter(
        frame,
        x="average_montly_hours",
        y="satisfaction_level",
        color="Status",
        color_discrete_map={"Masih bekerja": TEAL, "Keluar": CORAL},
        opacity=0.38,
        labels={
            "average_montly_hours": "Jam kerja bulanan",
            "satisfaction_level": "Tingkat kepuasan",
        },
    )
    figure.update_traces(
        hovertemplate=(
            "Jam kerja: %{x:.0f} jam"
            "<br>Kepuasan: %{y:.2f}"
            "<extra>%{fullData.name}</extra>"
        ),
        marker=dict(line=dict(width=0.4, color="#FFFFFF")),
    )
    figure.add_annotation(
        x=280,
        y=0.2,
        text="Beban tinggi<br>+ kepuasan rendah",
        showarrow=True,
        arrowhead=2,
        ax=-55,
        ay=-35,
        bgcolor="#FFFFFF",
        bordercolor=CORAL,
        borderwidth=1,
        font=dict(size=13, color="#7F1D1D"),
    )
    figure.update_layout(height=420, margin=dict(t=25, l=45, r=35, b=65))
    return _apply_plot_theme(figure)


def project_turnover(dataframe: pd.DataFrame) -> go.Figure:
    ordered = dataframe.sort_values("jumlah_proyek")
    rates = ordered["turnover_rate"].astype(float)
    counts = ordered["jumlah_karyawan"].astype(int)
    labels = [f"{int(value)} proyek" for value in ordered["jumlah_proyek"]]
    text = [
        f"{_format_number(rate * 100, 1)}% | n={_format_number(count, 0)}"
        for rate, count in zip(rates, counts)
    ]
    figure = go.Figure(
        go.Bar(
            x=rates * 100,
            y=labels,
            orientation="h",
            text=text,
            textposition="outside",
            cliponaxis=False,
            marker_color=[CORAL if rate > 0.30 else TEAL for rate in rates],
            customdata=counts,
            hovertemplate=(
                "%{y}<br>Karyawan keluar: %{x:.1f}%"
                "<br>Jumlah karyawan: %{customdata:,}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(
        title_text="Persentase karyawan yang keluar",
        ticksuffix="%",
        range=[0, min(110, max(40, float(rates.max() * 100 + 18)))],
    )
    figure.update_yaxes(title_text="")
    figure.update_layout(
        height=420,
        showlegend=False,
        margin=dict(t=25, l=45, r=95, b=65),
    )
    return _apply_plot_theme(figure)


def evaluation_charts(evaluation: pd.DataFrame, optimal_k: int) -> go.Figure:
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Elbow (WCSS)", "Silhouette"),
    )
    figure.add_scatter(
        x=evaluation["k"],
        y=evaluation["wcss"],
        mode="lines+markers",
        name="WCSS",
        marker_color=NAVY,
        hovertemplate="K: %{x}<br>WCSS: %{y:,.2f}<extra></extra>",
        row=1,
        col=1,
    )
    figure.add_scatter(
        x=evaluation["k"],
        y=evaluation["silhouette"],
        mode="lines+markers",
        name="Silhouette",
        marker_color=TEAL,
        hovertemplate="K: %{x}<br>Silhouette: %{y:.3f}<extra></extra>",
        row=1,
        col=2,
    )
    for column in (1, 2):
        figure.add_vline(
            x=optimal_k, line_dash="dash", line_color="#B45309", row=1, col=column
        )
    figure.update_xaxes(title_text="Jumlah kelompok (K)")
    figure.update_yaxes(title_text="WCSS", row=1, col=1)
    figure.update_yaxes(title_text="Silhouette", row=1, col=2)
    figure.update_layout(showlegend=False, margin=dict(t=70, l=45, r=35, b=60))
    return _apply_plot_theme(figure)


def cluster_map(
    points: pd.DataFrame,
    profiles: list[ClusterProfile],
    pca: PCA,
    kmeans: KMeans,
    added_point: PredictionResult | None = None,
) -> go.Figure:
    profile_by_cluster = {int(item["cluster"]): item for item in profiles}
    frame = points.sample(n=min(2000, len(points)), random_state=42).copy()
    frame["Persona"] = frame["Cluster"].map(
        lambda value: profile_by_cluster[int(value)]["persona"]
    )
    color_map = {
        item["persona"]: PERSONA_COLORS.get(
            item["persona"], item["badge_color"]
        )
        for item in profiles
    }
    symbol_by_persona = {
        profile["persona"]: PERSONA_SYMBOLS[index % len(PERSONA_SYMBOLS)]
        for index, profile in enumerate(profiles)
    }
    figure = px.scatter(
        frame,
        x="PCA1",
        y="PCA2",
        color="Persona",
        symbol="Persona",
        color_discrete_map=color_map,
        symbol_map=symbol_by_persona,
        category_orders={"Persona": [item["persona"] for item in profiles]},
        opacity=0.5,
        labels={
            "PCA1": "Peta kemiripan karyawan - arah 1",
            "PCA2": "Peta kemiripan karyawan - arah 2",
        },
    )
    figure.update_traces(
        marker=dict(size=7, line=dict(width=0.5, color="#FFFFFF")),
        hovertemplate="Persona: %{fullData.name}<extra></extra>",
    )

    center_coordinates = pca.transform(kmeans.cluster_centers_)
    for cluster, coordinates in enumerate(center_coordinates):
        profile = profile_by_cluster[cluster]
        persona = str(profile["persona"])
        color = color_map[persona]
        figure.add_trace(
            go.Scatter(
                x=[coordinates[0]],
                y=[coordinates[1]],
                mode="markers",
                marker=dict(
                    symbol=symbol_by_persona[persona],
                    size=19,
                    color=color,
                    line=dict(width=3, color="#FFFFFF"),
                ),
                name=f"Pusat kelompok {persona}",
                showlegend=False,
                hovertemplate=f"Pusat kelompok {escape(persona)}<extra></extra>",
            )
        )
        figure.add_annotation(
            x=coordinates[0],
            y=coordinates[1],
            text=f"<b>{escape(persona)}</b>",
            showarrow=False,
            yshift=22,
            bgcolor="#FFFFFF",
            bordercolor=color,
            borderwidth=1.5,
            borderpad=5,
            font=dict(size=13, color=color),
        )

    if added_point is not None:
        figure.add_trace(
            go.Scatter(
                x=[added_point["pca_x"]],
                y=[added_point["pca_y"]],
                mode="markers",
                marker=dict(
                    size=25,
                    color="#B45309",
                    symbol="star",
                    line=dict(width=3, color="#FFFFFF"),
                ),
                name="Karyawan yang dianalisis",
                hovertemplate="Karyawan yang dianalisis<extra></extra>",
            )
        )

    figure.update_layout(
        legend_title_text="Persona",
        height=560,
        margin=dict(t=30, l=50, r=35, b=75),
    )
    figure = _apply_plot_theme(figure)
    figure.update_layout(height=560)
    return figure


def cluster_distribution(dataframe: pd.DataFrame) -> go.Figure:
    required = {"Cluster", "Persona", "badge_color"}
    missing = sorted(required.difference(dataframe.columns))
    if missing:
        raise ValueError(
            "Data distribusi harus memiliki kolom: "
            + ", ".join(sorted(required))
            + "."
        )
    counts = (
        dataframe.groupby(
            ["Cluster", "Persona", "badge_color"], as_index=False, observed=True
        )
        .size()
        .rename(columns={"size": "Jumlah karyawan"})
    )
    color_map = {
        str(row["Persona"]): PERSONA_COLORS.get(
            str(row["Persona"]), str(row["badge_color"])
        )
        for _, row in counts.iterrows()
    }
    figure = px.pie(
        counts,
        values="Jumlah karyawan",
        names="Persona",
        color="Persona",
        color_discrete_map=color_map,
        hole=0.58,
    )
    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=(
            "Persona: %{label}"
            "<br>Jumlah karyawan: %{value:,}"
            "<br>Proporsi: %{percent}"
            "<extra></extra>"
        ),
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    figure.update_layout(height=390, margin=dict(t=25, l=30, r=30, b=25))
    return _apply_plot_theme(figure)


def employee_group_comparison(
    employee_values: Mapping[str, float],
    group_means: Mapping[str, float],
) -> go.Figure:
    labels = [FEATURE_LABELS.get(feature, feature) for feature in FEATURES]
    employee_indices = []
    employee_text = []
    mean_text = []
    for feature in FEATURES:
        mean = float(group_means[feature])
        if mean <= 0:
            raise ValueError(
                f"Rata-rata kelompok untuk {FEATURE_LABELS.get(feature, feature)} "
                "harus lebih besar dari nol."
            )
        value = float(employee_values[feature])
        employee_indices.append(value / mean * 100)
        employee_text.append(f"Input: {_format_number(value, 2)}")
        mean_text.append(f"Rata-rata: {_format_number(mean, 2)}")

    figure = go.Figure()
    figure.add_bar(
        y=labels,
        x=employee_indices,
        name="Karyawan",
        orientation="h",
        marker_color=TEAL,
        text=employee_text,
        textposition="outside",
        cliponaxis=False,
        customdata=[
            [float(employee_values[feature]), float(group_means[feature])]
            for feature in FEATURES
        ],
        hovertemplate=(
            "Karyawan: %{customdata[0]:.2f}"
            "<br>Rata-rata kelompok: %{customdata[1]:.2f}<extra></extra>"
        ),
    )
    figure.add_bar(
        y=labels,
        x=[100] * len(FEATURES),
        name="Rata-rata kelompok",
        orientation="h",
        marker_color=NAVY,
        text=mean_text,
        textposition="outside",
        cliponaxis=False,
        customdata=[
            [float(group_means[feature])] for feature in FEATURES
        ],
        hovertemplate="Rata-rata kelompok: %{customdata[0]:.2f}<extra></extra>",
    )
    figure.update_layout(
        barmode="group",
        height=450,
        margin=dict(t=30, l=170, r=140, b=70),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    figure.update_xaxes(
        title_text="Perbandingan relatif (rata-rata kelompok = 100)",
        rangemode="tozero",
    )
    figure.update_yaxes(title_text="", autorange="reversed")
    return _apply_plot_theme(figure)
