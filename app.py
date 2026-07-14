import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import numpy as np
import folium
from folium import plugins
import re
from pathlib import Path
from haversine import haversine
from scipy.spatial import Voronoi

# ──────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────────────────
CSV_PATH = Path("Coleta Geolocalizacional de Dados Saúde Informada .csv")
THRESHOLD_KM = 2.0

C = {
    'bg':           '#f0fdf4',
    'hdr_bg':       '#1b4332',
    'hdr_txt':      '#d8f3dc',
    'primary':      '#2d6a4f',
    'secondary':    '#40916c',
    'accent':       '#52b788',
    'light':        '#b7e4c7',
    'lighter':      '#d8f3dc',
    'white':        '#ffffff',
    'txt':          '#1b4332',
    'txt2':         '#495057',
    'border':       '#95d5b2',
    'warn':         '#e9c46a',
    'danger':       '#e76f51',
}

CAT_COLORS = {
    "UBS":                         "#2d6a4f",
    "UPA":                         "#e76f51",
    "SAMU":                        "#e9c46a",
    "Hospital":                    "#1b4332",
    "Maternidade":                 "#f4acb7",
    "CAPS":                        "#9b5de5",
    "CAPS / Acolhimento":          "#c77dff",
    "Centro Especializado":        "#4361ee",
    "Ambulatório / Especializado": "#4cc9f0",
    "Policlínica / Ambulatório":   "#74c69d",
    "Diagnóstico":                 "#adb5bd",
    "Ambulatório":                 "#95d5b2",
    "Clínica Especializada":       "#b7e4c7",
}

FOLIUM_CAT_COLORS = {
    "UBS": "blue", "UPA": "red", "SAMU": "orange",
    "Hospital": "darkred", "Maternidade": "pink",
    "CAPS": "purple", "CAPS / Acolhimento": "purple",
    "Centro Especializado": "green",
    "Ambulatório / Especializado": "cadetblue",
    "Policlínica / Ambulatório": "lightblue",
    "Diagnóstico": "gray", "Ambulatório": "lightgreen",
    "Clínica Especializada": "beige",
}

POPULATION = {
    'Centro': 18000, 'Cohab': 12000, 'Cohab II': 8000,
    'Nova Caxias': 9000, 'Castelo Branco': 7500, 'Pampulha': 7000,
    'Vila Paraiso': 5500, 'Sao Francisco': 6000, 'Vila Alecrim': 5000,
    'Santa Rita': 5500, 'Antenor Viana': 4500, 'Baixinha': 4000,
    'Salobro': 4000, 'Vila Sao Jose': 5000, 'Piraja': 4500,
    'Piquezeiro': 3500, 'Cangalheiro': 4000, 'Campo de Belem': 3500,
    'Campo de Belem II': 3000, 'Caldeiroes': 3500, 'Ponte': 3000,
    'Fazendinha': 3000, 'Mutirao': 4500, 'Trezidela': 3500,
    'Vila Arias': 4000, 'Luiza Queiroz': 3500, 'Itapecuruzinho': 3000,
    'Eugenio Coutinho': 3500, 'Bom Jesus': 3500, 'Buenos Aires': 2500,
    'Volta Redonda': 3500, 'Buriti Corrente': 1800, 'Chapada': 1500,
    'Breinho': 2000, 'Rodagem': 1500, 'Nazare do Bruno': 1800,
    'Caxirimbu': 1200, 'Povoado Santo Antonio': 1500,
    'Povoado Caxirimbu': 1000, 'Bau': 800,
}

# ──────────────────────────────────────────────────────────
# DADOS
# ──────────────────────────────────────────────────────────
def parse_coord(s):
    if pd.isna(s) or str(s).strip() in ('NULL', ''):
        return None
    m = re.search(r'-?\d+\.?\d*,\s*-?\d+\.?\d*', str(s))
    if m:
        lat, lon = map(float, m.group(0).split(','))
        if -5.5 < lat < -4.5 and -44.0 < lon < -42.5:
            return (lat, lon)
    return None

df_raw = pd.read_csv(CSV_PATH)
df_raw['coord'] = df_raw['Coordenada de Localização'].apply(parse_coord)
df = df_raw.dropna(subset=['coord']).reset_index(drop=True)

# ──────────────────────────────────────────────────────────
# GRAFO
# ──────────────────────────────────────────────────────────
G = nx.Graph()
for _, r in df.iterrows():
    G.add_node(r['Nome'], pos=r['coord'], categoria=r['Categoria'], bairro=r['Bairro'])

node_list = list(G.nodes(data=True))
for i, (n1, d1) in enumerate(node_list):
    for j, (n2, d2) in enumerate(node_list):
        if i < j and haversine(d1['pos'], d2['pos']) <= THRESHOLD_KM:
            G.add_edge(n1, n2, distance=haversine(d1['pos'], d2['pos']))

coloring = nx.greedy_color(G, strategy='largest_first')
chromatic_n = max(coloring.values()) + 1 if coloring else 0

# ──────────────────────────────────────────────────────────
# MAPA FOLIUM
# ──────────────────────────────────────────────────────────
def make_map(cat_filter='Todos'):
    m = folium.Map(location=[-4.865, -43.36], zoom_start=13, tiles="CartoDB positron")
    data = df if cat_filter == 'Todos' else df[df['Categoria'] == cat_filter]
    node_set = set(data['Nome'])

    feature_groups = {}
    for cat in data['Categoria'].unique():
        feature_groups[cat] = folium.FeatureGroup(name=cat, show=True)

    for _, r in data.iterrows():
        lat, lon = r['coord']
        cat = r['Categoria']
        popup = (
            f"<div style='font-family:Helvetica,Arial,sans-serif;min-width:200px'>"
            f"<b style='color:#1b4332'>{r['Nome']}</b><br>"
            f"<span style='color:#2d6a4f'>Bairro:</span> {r['Bairro']}<br>"
            f"<span style='color:#2d6a4f'>Categoria:</span> {cat}<br>"
            f"<span style='color:#2d6a4f'>Cor cromática:</span> {coloring.get(r['Nome'], 'N/A')}"
            f"</div>"
        )
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup, max_width=280),
            tooltip=r['Nome'],
            icon=folium.Icon(color=FOLIUM_CAT_COLORS.get(cat, 'black'), icon='plus', prefix='fa'),
        ).add_to(feature_groups[cat])

    for u, v in G.edges():
        if u in node_set and v in node_set:
            lat1, lon1 = G.nodes[u]['pos']
            lat2, lon2 = G.nodes[v]['pos']
            folium.PolyLine(
                [[lat1, lon1], [lat2, lon2]],
                weight=1.5, color='#40916c', opacity=0.25
            ).add_to(m)

    for fg in feature_groups.values():
        fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    plugins.Fullscreen().add_to(m)
    return m._repr_html_()

# ──────────────────────────────────────────────────────────
# VISUALIZAÇÕES PLOTLY
# ──────────────────────────────────────────────────────────
CHROM_PALETTE = [
    '#2d6a4f','#e76f51','#e9c46a','#4361ee',
    '#9b5de5','#f4acb7','#4cc9f0','#95d5b2','#ff9f1c','#2ec4b6',
]

def _edge_traces(layout):
    ex, ey = [], []
    for u, v in G.edges():
        x1, y1 = layout[u]; x2, y2 = layout[v]
        ex += [x1, x2, None]; ey += [y1, y2, None]
    return go.Scatter(x=ex, y=ey, mode='lines',
                      line=dict(width=0.8, color='#b7e4c7'),
                      hoverinfo='none', name='Arestas', showlegend=False)

def fig_graph_coloring():
    node_x, node_y, node_col, hover = [], [], [], []
    for n in G.nodes():
        lat, lon = G.nodes[n]['pos']
        node_x.append(lon); node_y.append(lat)
        c = coloring.get(n, 0)
        node_col.append(CHROM_PALETTE[c % len(CHROM_PALETTE)])
        hover.append(f"<b>{n}</b><br>Bairro: {G.nodes[n]['bairro']}<br>"
                     f"Categoria: {G.nodes[n]['categoria']}<br>Cor cromática: {c}")

    ex, ey = [], []
    for u, v in G.edges():
        la1, lo1 = G.nodes[u]['pos']; la2, lo2 = G.nodes[v]['pos']
        ex += [lo1, lo2, None]; ey += [la1, la2, None]

    fig = go.Figure([
        go.Scatter(x=ex, y=ey, mode='lines',
                   line=dict(width=1, color='#95d5b2'), hoverinfo='none',
                   name='Arestas', showlegend=False),
        go.Scatter(x=node_x, y=node_y, mode='markers',
                   marker=dict(size=11, color=node_col, line=dict(width=1.5, color='#1b4332')),
                   text=hover, hovertemplate='%{text}<extra></extra>', name='Unidades'),
    ])
    fig.update_layout(
        title=dict(text=f'Coloração por Proximidade Geográfica (threshold {THRESHOLD_KM}km) — nº cromático: {chromatic_n}',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', showlegend=False,
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude',  gridcolor='#e8f5e9'),
        margin=dict(l=50, r=30, t=60, b=50),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif'),
        annotations=[dict(
            text=f"Nós: {G.number_of_nodes()} · Arestas: {G.number_of_edges()} · Cores: {chromatic_n}",
            xref='paper', yref='paper', x=0, y=-0.13,
            showarrow=False, font=dict(size=11, color=C['secondary'])
        )],
    )
    return fig


def fig_forceatlas2():
    pos = nx.spring_layout(G, k=2.2, iterations=120, seed=42)
    traces = [_edge_traces(pos)]
    seen = set()
    for n in G.nodes():
        cat = G.nodes[n]['categoria']
        x, y = pos[n]
        traces.append(go.Scatter(
            x=[x], y=[y], mode='markers',
            marker=dict(size=12, color=CAT_COLORS.get(cat, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{n}</b><br>Bairro: {G.nodes[n]['bairro']}<br>Categoria: {cat}"],
            hovertemplate='%{text}<extra></extra>',
            name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text='Rede de Serviços — Layout ForceAtlas2/Spring por Categoria',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=20, r=200, t=60, b=20),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif'),
    )
    return fig


def fig_voronoi():
    cx, cy = -43.36, -4.865
    mask = (abs(df['coord'].apply(lambda p: p[1]) - cx) < 0.12) & \
           (abs(df['coord'].apply(lambda p: p[0]) - cy) < 0.12)
    sub = df[mask].reset_index(drop=True)
    if len(sub) < 4:
        sub = df

    pts = np.array([[r['coord'][1], r['coord'][0]] for _, r in sub.iterrows()])
    cats = sub['Categoria'].tolist()
    names = sub['Nome'].tolist()

    fig = go.Figure()
    try:
        vor = Voronoi(pts)
        xmin, xmax = pts[:, 0].min() - 0.005, pts[:, 0].max() + 0.005
        ymin, ymax = pts[:, 1].min() - 0.005, pts[:, 1].max() + 0.005

        for simplex in vor.ridge_vertices:
            if -1 not in simplex:
                p0, p1 = vor.vertices[simplex[0]], vor.vertices[simplex[1]]
                if (xmin < p0[0] < xmax and ymin < p0[1] < ymax and
                        xmin < p1[0] < xmax and ymin < p1[1] < ymax):
                    fig.add_trace(go.Scatter(
                        x=[p0[0], p1[0]], y=[p0[1], p1[1]], mode='lines',
                        line=dict(color='#74c69d', width=1.2),
                        hoverinfo='none', showlegend=False,
                    ))
    except Exception:
        pass

    seen = set()
    for i, (coord, cat, name) in enumerate(zip(pts, cats, names)):
        fig.add_trace(go.Scatter(
            x=[coord[0]], y=[coord[1]], mode='markers',
            marker=dict(size=10, color=CAT_COLORS.get(cat, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{name}</b><br>Categoria: {cat}"],
            hovertemplate='%{text}<extra></extra>',
            name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)

    fig.update_layout(
        title=dict(text='Diagrama de Voronoi — Regiões de Influência por Unidade (área urbana)',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9', scaleanchor='x', scaleratio=1),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', hovermode='closest',
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=50, r=200, t=60, b=50),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif'),
    )
    return fig


def fig_scheduling():
    pos = nx.spring_layout(G, k=1.8, iterations=100, seed=77)
    traces = [_edge_traces(pos)]
    for c in range(chromatic_n):
        nodes = [n for n, col in coloring.items() if col == c]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes],
            y=[pos[n][1] for n in nodes],
            mode='markers',
            marker=dict(size=12, color=CHROM_PALETTE[c % len(CHROM_PALETTE)],
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{n}</b><br>Grupo {c+1}<br>Categoria: {G.nodes[n]['categoria']}" for n in nodes],
            hovertemplate='%{text}<extra></extra>',
            name=f"Grupo {c + 1}",
        ))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(
            text=f'Coloração para Alocação de Serviços — {chromatic_n} grupos sem conflito',
            font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=20, r=160, t=60, b=20),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif'),
    )
    return fig


# ──────────────────────────────────────────────────────────
# HELPERS DE ESTILO
# ──────────────────────────────────────────────────────────
def card(extra=None):
    s = {'background': C['white'], 'border': f"2px solid {C['light']}",
         'padding': '24px', 'marginBottom': '20px'}
    if extra:
        s.update(extra)
    return s

TAB_S = {
    'padding': '12px 28px', 'fontWeight': '500', 'fontSize': '14px',
    'backgroundColor': C['lighter'], 'color': C['primary'],
    'border': f"2px solid {C['light']}", 'borderRadius': '0',
}
TAB_SEL = {**TAB_S, 'backgroundColor': C['primary'], 'color': 'white', 'borderColor': C['primary']}

HDR = {
    'backgroundColor': C['hdr_bg'], 'color': C['hdr_txt'],
    'padding': '18px 40px', 'borderBottom': f"4px solid {C['secondary']}",
    'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between',
}

# ──────────────────────────────────────────────────────────
# LAYOUT: LANDING
# ──────────────────────────────────────────────────────────
n_units  = len(df)
n_bairros = df['Bairro'].nunique()
n_cats   = df['Categoria'].nunique()

def _stat(value, label):
    return html.Div([
        html.Span(str(value), style={'fontSize': '2.2rem', 'fontWeight': '700', 'color': '#74c69d'}),
        html.Span(f" {label}", style={'color': C['lighter'], 'marginRight': '32px'}),
    ])

def _step(n, title, text):
    return html.Div([
        html.Div(str(n), style={
            'width': '34px', 'height': '34px', 'backgroundColor': C['primary'],
            'color': 'white', 'display': 'flex', 'alignItems': 'center',
            'justifyContent': 'center', 'fontWeight': '700', 'marginBottom': '10px',
        }),
        html.H4(title, style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '8px'}),
        html.P(text, style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6', 'margin': '0'}),
    ], style={
        'flex': '1', 'padding': '16px',
        'borderRight': f"2px solid {C['lighter']}",
        'minWidth': '200px',
    })

def _ack(label, title, sub, border_color):
    return html.Div([
        html.Div(label, style={
            'fontWeight': '700', 'fontSize': '1.3rem', 'color': C['primary'],
            'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '8px', 'marginBottom': '8px',
        }),
        html.P(title, style={'fontWeight': '600', 'color': C['primary'], 'marginBottom': '4px'}),
        html.P(sub, style={'fontSize': '0.88rem', 'color': C['txt2'], 'margin': '0'}),
    ], style={**card({'borderTop': f'4px solid {border_color}', 'flex': '1', 'marginBottom': '0'})})

def _ref(authors, title, rest):
    return html.P([authors, html.Strong(title), rest],
                  style={'marginBottom': '14px', 'lineHeight': '1.7', 'fontSize': '0.9rem'})

tab_landing = html.Div([
    # Hero
    html.Div([
        html.H1("Saúde Informada", style={
            'fontSize': '2.6rem', 'fontWeight': '700', 'color': C['hdr_txt'],
            'margin': '0 0 6px',
        }),
        html.H2(
            "Mapeamento e Análise dos Serviços de Saúde Pública em Caxias-MA via Teoria dos Grafos",
            style={'fontSize': '1.15rem', 'fontWeight': '400', 'color': C['lighter'], 'margin': '0 0 16px'},
        ),
        html.P(
            "Plataforma interativa que integra dados geoespaciais validados a algoritmos de coloração de "
            "grafos para revelar padrões de cobertura, redundâncias e lacunas na rede pública de saúde.",
            style={'color': '#b7e4c7', 'maxWidth': '720px', 'lineHeight': '1.7', 'marginBottom': '24px'},
        ),
        html.Div([_stat(n_units, 'unidades'), _stat(n_bairros, 'bairros'),
                  _stat(n_cats, 'categorias'), _stat(chromatic_n, 'cores')],
                 style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style={
        'backgroundColor': C['hdr_bg'], 'padding': '50px 60px',
        'borderBottom': f"4px solid {C['secondary']}",
    }),

    # Content
    html.Div([
        # Sobre + Objetivos
        html.Div([
            html.Div([
                html.H3("Sobre o Projeto", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
                }),
                html.P(
                    "Esta pesquisa integra dados geoespaciais dos serviços de saúde pública do município "
                    "de Caxias-MA a técnicas computacionais de teoria dos grafos. A coloração de grafos, "
                    "técnica que atribui rótulos a vértices de modo que nenhum par adjacente compartilhe o "
                    "mesmo rótulo, é utilizada para identificar padrões de cobertura, conflitos de "
                    "proximidade e complementaridades na rede de atenção à saúde.",
                    style={'lineHeight': '1.7', 'color': C['txt2']},
                ),
                html.P(
                    "O dataset foi coletado e validado a partir do CNES/DATASUS e verificação in loco via "
                    "Google Maps, abrangendo UBS, hospitais, CAPS, UPA, SAMU, centros especializados, "
                    "ambulatórios e serviços de diagnóstico do município.",
                    style={'lineHeight': '1.7', 'color': C['txt2'], 'marginBottom': '0'},
                ),
            ], style={**card(), 'flex': '1', 'marginRight': '20px'}),

            html.Div([
                html.H3("Objetivos", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
                }),
                html.Ul([
                    html.Li(t, style={'marginBottom': '8px'}) for t in [
                        "Mapear e catalogar serviços de saúde de Caxias-MA com coordenadas geográficas validadas",
                        "Modelar a distribuição como grafo de proximidade (threshold 2 km)",
                        "Aplicar algoritmos de coloração para análise de conflitos e cobertura",
                        "Identificar gaps e redundâncias na rede de atenção à saúde",
                        "Comparar abordagens distintas de abstração e visualização de redes de saúde",
                        "Disponibilizar visualizações interativas para apoio à gestão em saúde pública",
                    ]
                ], style={'lineHeight': '1.8', 'color': C['txt2'], 'paddingLeft': '20px', 'margin': '0'}),
            ], style={**card(), 'flex': '1'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),

        # Metodologia
        html.Div([
            html.H3("Metodologia", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
            }),
            html.Div([
                _step(1, "Coleta de Dados",
                      "Levantamento geoespacial via CNES/DATASUS e Google Maps. "
                      "Validação manual de coordenadas e categorização por tipo de serviço."),
                _step(2, "Construção do Grafo",
                      "Vértices = unidades de saúde; arestas = proximidade ≤ 2km (haversine). "
                      "Grafo não-direcionado implementado com NetworkX."),
                _step(3, "Coloração Cromática",
                      f"Algoritmo greedy (largest_first) determinou número cromático χ = {chromatic_n}. "
                      "Cada cor representa um grupo de serviços sem conflito de adjacência."),
                html.Div([
                    html.Div("4", style={
                        'width': '34px', 'height': '34px', 'backgroundColor': C['primary'],
                        'color': 'white', 'display': 'flex', 'alignItems': 'center',
                        'justifyContent': 'center', 'fontWeight': '700', 'marginBottom': '10px',
                    }),
                    html.H4("Análise e Visualização", style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '8px'}),
                    html.P(
                        "Diagramas de Voronoi, grafos com force-layout e mapa interativo revelam "
                        "cobertura por bairro, gaps e padrões topológicos da rede.",
                        style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6', 'margin': '0'},
                    ),
                ], style={'flex': '1', 'padding': '16px', 'minWidth': '200px'}),
            ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        ], style=card()),

        # Agradecimentos
        html.Div([
            html.H3("Agradecimentos", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
            }),
            html.Div([
                _ack("IFMA", "Instituto Federal do Maranhão",
                     "Campus Caxias pelo suporte institucional e infraestrutura de pesquisa",
                     C['primary']),
                _ack("PRPGI", "Pró-Reitoria de Pesquisa, Pós-Graduação e Inovação",
                     "Pelo apoio ao desenvolvimento da pesquisa científica no IFMA",
                     C['secondary']),
                _ack("SUS", "Sistema Único de Saúde",
                     "Pelo suporte na disponibilização dos dados públicos de saúde (CNES/DATASUS)",
                     C['accent']),
                _ack("Orientação", "Prof. Dr. Luis Fernando Maia Santos Silva",
                     "Pela orientação, dedicação e suporte ao longo de toda a pesquisa",
                     C['lighter']),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px'}),
        ], style=card()),

        # Referências ABNT
        html.Div([
            html.H3("Referências", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
            }),
            html.Div([
                _ref("AURENHAMMER, Franz; KLEIN, Rolf; LEE, Der-Tsai. ",
                     "Voronoi Diagrams and Delaunay Triangulations.",
                     " Singapore: World Scientific, 2013."),
                _ref("BRASIL. Ministério da Saúde. ",
                     "Cadastro Nacional de Estabelecimentos de Saúde (CNES).",
                     " Disponível em: <http://cnes.datasus.gov.br>. Acesso em: 5 jul. 2026."),
                _ref("DABIRE, Inoussa et al. ",
                     "Health Centers Network Analysis with Gephi and ForceAtlas2.",
                     " 2025."),
                _ref("JENSEN, Tommy R.; TOFT, Bjarne. ",
                     "Graph Coloring Problems.",
                     " New York: Wiley-Interscience, 1995."),
                _ref("LEWIS, Rhyd. ",
                     "Graph Colouring: A Visual Tour.",
                     " arXiv, 2026. Disponível em: <https://arxiv.org/>. Acesso em: 5 jul. 2026."),
                _ref("MARX, Daniel. Graph Coloring Problems and Their Applications in Scheduling. ",
                     "Periodica Polytechnica Electrical Engineering,",
                     " v. 48, n. 1-2, p. 11-16, 2004."),
                _ref("NETWORKX DEVELOPERS. ",
                     "NetworkX: Network Analysis in Python.",
                     " Disponível em: <https://networkx.org>. Acesso em: 5 jul. 2026."),
                _ref("OKABE, Atsuyuki et al. ",
                     "Spatial Tessellations: Concepts and Applications of Voronoi Diagrams.",
                     " 2. ed. Chichester: John Wiley & Sons, 2000."),
            ], style={'color': C['txt2']}),
        ], style=card()),

    ], style={'padding': '28px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
])


# ──────────────────────────────────────────────────────────
# LAYOUT: MAPA E COBERTURA
# ──────────────────────────────────────────────────────────
all_cats = ['Todos'] + sorted(df['Categoria'].unique().tolist())

tab_mapa = html.Div([
    html.Div([
        # Sidebar
        html.Div([
            html.H3("Filtros", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px', 'marginBottom': '16px',
            }),
            html.Label("Tipo de Serviço", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
            dcc.Dropdown(
                id='filter-cat',
                options=[{'label': c, 'value': c} for c in all_cats],
                value='Todos', clearable=False,
                style={'marginTop': '8px', 'marginBottom': '20px'},
            ),
            html.H4("Resumo", style={
                'color': C['primary'], 'borderBottom': f"1px solid {C['light']}",
                'paddingBottom': '8px', 'marginTop': '0',
            }),
            html.Div(id='map-summary'),
            html.H4("Legenda", style={
                'color': C['primary'], 'marginTop': '20px',
                'borderBottom': f"1px solid {C['light']}", 'paddingBottom': '8px',
            }),
            html.Div([
                html.Div([
                    html.Div(style={
                        'width': '13px', 'height': '13px',
                        'backgroundColor': col, 'marginRight': '8px', 'flexShrink': '0',
                    }),
                    html.Span(cat, style={'fontSize': '0.8rem', 'color': C['txt2']}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'})
                for cat, col in CAT_COLORS.items()
            ]),
        ], style={
            'width': '250px', 'flexShrink': '0',
            'backgroundColor': C['white'], 'border': f"2px solid {C['light']}",
            'padding': '20px', 'overflowY': 'auto',
        }),
        # Map
        html.Div([
            html.Iframe(id='map-frame', srcDoc='',
                        style={'width': '100%', 'height': '100%', 'border': 'none'}),
        ], style={
            'flex': '1', 'height': '580px',
            'border': f"2px solid {C['light']}", 'borderLeft': 'none',
        }),
    ], style={'display': 'flex', 'marginBottom': '20px', 'height': '580px'}),

    # Charts row
    html.Div([
        html.Div([
            dcc.Graph(id='bar-chart', config={'displayModeBar': False}, style={'height': '360px'}),
        ], style={**card({'flex': '1.6', 'marginRight': '20px', 'padding': '16px', 'marginBottom': '0'})}),

        html.Div([
            html.H4("Distribuição por Categoria", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '8px',
            }),
            dcc.Graph(id='pie-chart', config={'displayModeBar': False}, style={'height': '300px'}),
        ], style={**card({'flex': '1', 'padding': '16px', 'marginBottom': '0'})}),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '20px'}),

    # Table
    html.Div([
        html.H3("Cobertura por Bairro", style={
            'color': C['primary'], 'marginTop': '0',
            'borderBottom': f"3px solid {C['accent']}", 'paddingBottom': '10px',
        }),
        html.Div(id='cov-table'),
    ], style=card()),

], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto',
          'fontFamily': 'Helvetica Neue, Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT: GRAFOS
# ──────────────────────────────────────────────────────────
def method_section(title, authors, year, source, description, figure):
    return html.Div([
        html.Div([
            html.H3(title, style={'color': C['primary'], 'margin': '0 0 4px'}),
            html.P(f"{authors} — {source}, {year}", style={
                'color': C['txt2'], 'fontSize': '0.86rem', 'fontStyle': 'italic', 'margin': '0 0 12px',
            }),
            html.P(description, style={
                'color': C['txt2'], 'fontSize': '0.91rem', 'lineHeight': '1.6',
                'borderLeft': f"4px solid {C['accent']}", 'paddingLeft': '14px', 'margin': '0',
            }),
        ], style={
            'backgroundColor': C['bg'], 'border': f"1px solid {C['light']}",
            'padding': '16px', 'marginBottom': '16px',
        }),
        dcc.Graph(figure=figure,
                  config={'displayModeBar': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']},
                  style={'height': '520px'}),
    ], style={**card({'marginBottom': '28px'})})

tab_grafos = html.Div([
    html.Div([
        html.H2("Visualização de Grafos", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Quatro metodologias de abstração e visualização aplicadas à rede de serviços de Caxias-MA. "
            "Cada abordagem revela dimensões complementares da distribuição e cobertura.",
            style={'color': C['txt2'], 'marginBottom': '28px'},
        ),

        method_section(
            "Graph Colouring: A Visual Tour",
            "Rhyd Lewis", "2026", "arXiv",
            f"Arestas conectam unidades a menos de {THRESHOLD_KM}km (distância haversine). "
            "Coloração cromática (greedy, largest_first) destaca conflitos de proximidade, "
            "serviços do mesmo tipo muito próximos e complementaridades entre categorias distintas. "
            "Posições dos nós correspondem às coordenadas geográficas reais.",
            fig_graph_coloring(),
        ),

        method_section(
            "Health Centers Network Analysis with Gephi and ForceAtlas2",
            "Dabire et al.", "2025", "Gephi / ForceAtlas2",
            "Layout baseado em força (spring layout como aproximação do ForceAtlas2): "
            "a topologia da rede emerge da estrutura de conexões, independente da posição geográfica. "
            "Nós coloridos por categoria de serviço. A proximidade visual reflete densidade de conexões.",
            fig_forceatlas2(),
        ),

        method_section(
            "Voronoi Diagrams em Facility Location",
            "Aurenhammer, Klein & Lee; Okabe et al.", "2000/2013", "Geometria Computacional",
            "Tesselação de Voronoi sobre as coordenadas das unidades da área urbana central de Caxias. "
            "Cada polígono delimita a região de influência natural de uma unidade, "
            "onde ela é o serviço geograficamente mais próximo. "
            "Facilita identificação de gaps de cobertura, sobreposição e redundâncias.",
            fig_voronoi(),
        ),

        method_section(
            "Graph Coloring Applied to Service Allocation and Scheduling",
            "Marx, D.", "2004", "Periodica Polytechnica Electrical Engineering",
            f"Extensão da coloração ao problema de alocação de recursos: cada grupo de cor representa "
            f"um conjunto de unidades que podem operar em um mesmo turno ou receber a mesma categoria "
            f"de recurso sem conflito. Com χ = {chromatic_n}, a rede requer no mínimo {chromatic_n} "
            f"grupos para alocação sem conflito entre unidades dentro do raio de {THRESHOLD_KM}km.",
            fig_scheduling(),
        ),

    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
], style={'fontFamily': 'Helvetica Neue, Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ──────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="Saúde Informada (Caxias-MA)",
                suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.Div([
        html.Div([
            html.Span("Saúde Informada", style={
                'fontSize': '1.4rem', 'fontWeight': '700', 'color': C['hdr_txt'],
            }),
            html.Span(" · ", style={'color': C['accent'], 'margin': '0 8px'}),
            html.Span("Caxias-MA", style={'fontSize': '1rem', 'color': C['lighter']}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div([
            html.Span(lbl, style={
                'fontSize': '0.82rem', 'color': C['accent'],
                'border': f"1px solid {C['accent']}", 'padding': '2px 10px', 'marginLeft': '8px',
            }) for lbl in ['IFMA', 'PRPGI', 'SUS']
        ], style={'display': 'flex'}),
    ], style=HDR),

    dcc.Tabs(id='tabs', value='landing', children=[
        dcc.Tab(label='Início',              value='landing', style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Mapa e Cobertura',    value='mapa',    style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Visualização de Grafos', value='grafos', style=TAB_S, selected_style=TAB_SEL),
    ], style={'backgroundColor': C['lighter'], 'borderBottom': f"2px solid {C['light']}"}),

    html.Div(id='content'),

    html.Div([
        html.Div("Saúde Informada · IFMA Campus Caxias · PRPGI · 2025–2026",
                 style={'color': C['accent']}),
        html.Div("Dados: CNES/DATASUS · SUS · Coleta primária",
                 style={'color': C['accent'], 'fontSize': '0.83rem'}),
    ], style={
        'backgroundColor': C['hdr_bg'], 'borderTop': f"3px solid {C['secondary']}",
        'padding': '14px 40px', 'display': 'flex', 'justifyContent': 'space-between',
        'alignItems': 'center', 'fontSize': '0.88rem',
        'fontFamily': 'Helvetica Neue, Helvetica, Arial, sans-serif',
    }),
], style={'fontFamily': 'Helvetica Neue, Helvetica, Arial, sans-serif',
          'backgroundColor': C['bg'], 'minHeight': '100vh'})


# ──────────────────────────────────────────────────────────
# CALLBACKS
# ──────────────────────────────────────────────────────────
@app.callback(Output('content', 'children'), Input('tabs', 'value'))
def render_tab(tab):
    if tab == 'landing': return tab_landing
    if tab == 'mapa':    return tab_mapa
    if tab == 'grafos':  return tab_grafos
    return html.Div()


@app.callback(
    Output('map-frame',   'srcDoc'),
    Output('map-summary', 'children'),
    Output('bar-chart',   'figure'),
    Output('pie-chart',   'figure'),
    Output('cov-table',   'children'),
    Input('filter-cat',   'value'),
)
def update_mapa(cat):
    fdf = df if cat == 'Todos' else df[df['Categoria'] == cat]

    # Map
    map_html = make_map(cat)

    # Summary
    summary = html.Div([
        html.Div([
            html.Span(str(len(fdf)), style={'fontSize': '2rem', 'fontWeight': '700',
                                            'color': C['primary'], 'display': 'block'}),
            html.Span("unidades", style={'fontSize': '0.78rem', 'color': C['txt2']}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(str(fdf['Bairro'].nunique()), style={'fontSize': '1.5rem', 'fontWeight': '700',
                                                            'color': C['secondary'], 'display': 'block'}),
            html.Span("bairros", style={'fontSize': '0.78rem', 'color': C['txt2']}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(str(fdf['Categoria'].nunique()), style={'fontSize': '1.5rem', 'fontWeight': '700',
                                                               'color': C['accent'], 'display': 'block'}),
            html.Span("categorias", style={'fontSize': '0.78rem', 'color': C['txt2']}),
        ]),
    ])

    # Bar chart
    bc = fdf.groupby('Bairro').size().reset_index(name='n').nlargest(20, 'n')
    bar_fig = go.Figure(go.Bar(
        x=bc['Bairro'], y=bc['n'],
        marker_color=C['secondary'],
        hovertemplate='<b>%{x}</b><br>Unidades: %{y}<extra></extra>',
    ))
    bar_fig.update_layout(
        title=dict(text='Unidades por Bairro (Top 20)', font=dict(size=13, color=C['primary'])),
        xaxis=dict(tickangle=-45, gridcolor='#e8f5e9'),
        yaxis=dict(title='Unidades', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        margin=dict(l=40, r=20, t=50, b=120),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif', color=C['txt']),
        showlegend=False,
    )

    # Pie chart
    pc = fdf['Categoria'].value_counts().reset_index()
    pc.columns = ['cat', 'n']
    pie_fig = go.Figure(go.Pie(
        labels=pc['cat'], values=pc['n'], hole=0.4,
        marker=dict(colors=[CAT_COLORS.get(c, C['secondary']) for c in pc['cat']]),
        textinfo='percent', textfont=dict(size=10),
    ))
    pie_fig.update_layout(
        showlegend=True, paper_bgcolor='white',
        legend=dict(font=dict(size=10), x=1.0),
        margin=dict(l=0, r=80, t=0, b=0),
        font=dict(family='Helvetica Neue, Helvetica, Arial, sans-serif'),
    )

    # Coverage table
    rows = []
    for bairro, grp in fdf.groupby('Bairro'):
        n_u = len(grp)
        pop = POPULATION.get(bairro, 2000)
        ratio = (n_u / pop) * 1000
        pct = min(100.0, ratio * 20)
        if ratio >= 0.8:   status, sc = 'Adequada',   C['secondary']
        elif ratio >= 0.3: status, sc = 'Parcial',    C['warn']
        else:              status, sc = 'Deficiente',  C['danger']
        rows.append(dict(bairro=bairro, pop=pop, n=n_u,
                         ratio=ratio, pct=pct, status=status, sc=sc))
    rows.sort(key=lambda x: x['n'], reverse=True)

    TH = lambda txt: html.Th(txt, style={
        'padding': '10px 14px', 'backgroundColor': C['primary'], 'color': 'white',
        'fontWeight': '600', 'fontSize': '0.85rem', 'whiteSpace': 'nowrap',
        'textAlign': 'left' if txt == 'Bairro' else 'right' if txt != 'Status' else 'center',
    })
    def TD(txt, align='left', bold=False, color=None):
        return html.Td(txt, style={
            'padding': '8px 14px', 'fontSize': '0.85rem', 'textAlign': align,
            'fontWeight': '600' if bold else 'normal',
            'color': color or C['txt'],
        })

    table = html.Table([
        html.Thead(html.Tr([
            TH('Bairro'), TH('Pop. Estimada'), TH('Unidades'),
            TH('Unid./1000 hab.'), TH('Cobertura (%)'), TH('Status'),
        ])),
        html.Tbody([
            html.Tr([
                TD(r['bairro']),
                TD(f"{r['pop']:,}".replace(',', '.'), align='right', color=C['txt2']),
                TD(str(r['n']), align='right', bold=True, color=C['primary']),
                TD(f"{r['ratio']:.3f}", align='right', color=C['txt2']),
                html.Td([
                    html.Div(style={'height': '8px', 'backgroundColor': C['lighter']}),
                    html.Div(style={
                        'height': '8px', 'backgroundColor': r['sc'],
                        'width': f"{r['pct']:.1f}%", 'marginTop': '-8px',
                    }),
                    html.Div(f"{r['pct']:.1f}%", style={
                        'fontSize': '0.78rem', 'color': C['txt2'],
                        'textAlign': 'right', 'marginTop': '3px',
                    }),
                ], style={'padding': '8px 14px', 'minWidth': '110px'}),
                html.Td(html.Span(r['status'], style={
                    'backgroundColor': r['sc'],
                    'color': 'white' if r['status'] != 'Parcial' else '#1b4332',
                    'padding': '3px 10px', 'fontSize': '0.8rem', 'fontWeight': '600',
                }), style={'padding': '8px 14px', 'textAlign': 'center'}),
            ], style={
                'backgroundColor': 'white' if i % 2 == 0 else C['bg'],
                'borderBottom': f"1px solid {C['lighter']}",
            })
            for i, r in enumerate(rows)
        ]),
    ], style={'width': '100%', 'borderCollapse': 'collapse',
              'fontFamily': 'Helvetica Neue, Helvetica, Arial, sans-serif'})

    return map_html, summary, bar_fig, pie_fig, table


# ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
