import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from core.contracts import ClusterProfile, PredictionResult

NAVY = "#1E3A8A"
TEAL = "#0D9488"
PLOT_FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"


def _apply_plot_theme(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT, color="#1E293B", size=12),
        title=dict(x=0.01, xanchor="left", font=dict(size=17, color=NAVY)),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="left",
            x=0,
            title_text="",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#CBD5E1",
            font=dict(family=PLOT_FONT, color="#1E293B", size=12),
        ),
        margin=dict(t=65, l=30, r=25, b=65),
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        zeroline=False,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        zeroline=False,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
    )
    return figure


def summary_scatter(dataframe: pd.DataFrame) -> go.Figure:
    frame = dataframe.copy()
    frame["Status"] = frame["left"].map({0: "Masih bekerja", 1: "Keluar"})
    figure = px.scatter(
        frame,
        x="average_montly_hours",
        y="satisfaction_level",
        color="Status",
        color_discrete_map={"Masih bekerja": TEAL, "Keluar": "#DC2626"},
        opacity=0.65,
        labels={
            "average_montly_hours": "Jam kerja bulanan",
            "satisfaction_level": "Tingkat kepuasan",
        },
        title="Jam kerja bulanan vs tingkat kepuasan",
    )
    figure.update_traces(
        hovertemplate=(
            "Jam kerja: %{x:.0f} jam"
            "<br>Kepuasan: %{y:.2f}"
            "<extra>%{fullData.name}</extra>"
        ),
        marker=dict(line=dict(width=0.5, color="#FFFFFF")),
    )
    return _apply_plot_theme(figure)


def project_turnover(dataframe: pd.DataFrame) -> go.Figure:
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(
        x=dataframe["jumlah_proyek"],
        y=dataframe["jumlah_karyawan"],
        name="Jumlah karyawan",
        marker_color=NAVY,
    )
    figure.add_scatter(
        x=dataframe["jumlah_proyek"],
        y=dataframe["turnover_rate"] * 100,
        name="Turnover rate",
        mode="lines+markers",
        marker_color=TEAL,
        secondary_y=True,
        hovertemplate=(
            "Jumlah proyek: %{x}"
            "<br>Turnover: %{y:.1f}%"
            "<extra></extra>"
        ),
    )
    figure.update_traces(
        selector=dict(type="bar"),
        hovertemplate="Jumlah proyek: %{x}<br>Karyawan: %{y:,}<extra></extra>",
    )
    figure.update_xaxes(title_text="Jumlah proyek")
    figure.update_yaxes(title_text="Jumlah karyawan", secondary_y=False)
    figure.update_yaxes(
        title_text="Turnover rate (%)",
        ticksuffix="%",
        range=[0, 100],
        secondary_y=True,
    )
    figure.update_layout(
        title="Distribusi karyawan dan turnover per jumlah proyek",
        legend_title_text="",
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
            x=optimal_k, line_dash="dash", line_color="#F59E0B", row=1, col=column
        )
    figure.update_xaxes(title_text="Jumlah klaster (K)")
    figure.update_yaxes(title_text="WCSS", row=1, col=1)
    figure.update_yaxes(title_text="Silhouette", row=1, col=2)
    figure.update_layout(showlegend=False, margin=dict(t=65, l=25, r=25, b=25))
    return _apply_plot_theme(figure)


def cluster_map(
    points: pd.DataFrame,
    profiles: list[ClusterProfile],
    pca: PCA,
    kmeans: KMeans,
    added_point: PredictionResult | None = None,
) -> go.Figure:
    profile_by_cluster = {int(item["cluster"]): item for item in profiles}
    frame = points.copy()
    frame["Persona"] = frame["Cluster"].map(
        lambda value: profile_by_cluster[int(value)]["persona"]
    )
    color_map = {
        item["persona"]: item["badge_color"] for item in profiles
    }
    figure = px.scatter(
        frame,
        x="PCA1",
        y="PCA2",
        color="Persona",
        color_discrete_map=color_map,
        opacity=0.65,
        labels={"PCA1": "Komponen utama 1", "PCA2": "Komponen utama 2"},
    )

    scaled_centers = kmeans.cluster_centers_
    centroid_coordinates = pca.transform(scaled_centers)
    for cluster, coordinates in enumerate(centroid_coordinates):
        profile = profile_by_cluster[cluster]
        figure.add_trace(
            go.Scatter(
                x=[coordinates[0]],
                y=[coordinates[1]],
                mode="markers+text",
                text=[f"Centroid {cluster}"],
                textposition="top center",
                marker=dict(
                    symbol="diamond",
                    size=18,
                    color=profile["badge_color"],
                    line=dict(width=2, color="#0F172A"),
                ),
                name=f"Centroid {cluster}",
                showlegend=False,
            )
        )
    if added_point is not None:
        figure.add_trace(
            go.Scatter(
                x=[added_point["pca_x"]],
                y=[added_point["pca_y"]],
                mode="markers",
                marker=dict(
                    size=20,
                    color="#D97706",
                    symbol="star",
                    line=dict(width=2, color="#0F172A"),
                ),
                name="Karyawan yang dianalisis",
                hovertemplate=(
                    "Karyawan yang dianalisis"
                    "<br>PC1: %{x:.2f}"
                    "<br>PC2: %{y:.2f}"
                    "<extra></extra>"
                ),
            )
        )

    variance = getattr(pca, "explained_variance_ratio_", None)
    if variance is not None and len(variance) >= 2:
        figure.update_xaxes(title_text=f"PC1 ({variance[0] * 100:.1f}% varians)")
        figure.update_yaxes(title_text=f"PC2 ({variance[1] * 100:.1f}% varians)")
    figure.update_layout(
        legend_title_text="Persona",
    )
    return _apply_plot_theme(figure)


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
    figure = px.pie(
        counts,
        values="Jumlah karyawan",
        names="Persona",
        color="Persona",
        color_discrete_map={
            str(persona): str(color)
            for persona, color in zip(counts["Persona"], counts["badge_color"])
        },
        hole=0.58,
        title="Distribusi hasil prediksi per klaster",
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
    return _apply_plot_theme(figure)
