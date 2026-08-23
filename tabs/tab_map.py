"""Aba 2 — Mapa.

Mapa Folium com filtro de categoria, filtro de raio de proximidade
(0.5/1/2/3/5 km, controla a camada de conexões do grafo) e marcadores
coloridos pela coloração cromática do grafo naquele raio.
"""
import folium
from dash import Input, Output, dcc, html

from colors import C, CAT_COLORS, CHROM_PALETTE, MAP_CENTER, RADII_KM
from components import card
from data_utils import POLI_CNES, POLI_NOME_CSV, df_all, df_geo
from graph_utils import build_graph, colorir_greedy

ALL_CATS = sorted(df_all['Categoria'].unique())


def make_map(cats, raio_km):
    m = folium.Map(location=list(MAP_CENTER), zoom_start=13, tiles="CartoDB positron")
    data = df_geo[df_geo['Categoria'].isin(cats)] if cats else df_geo.iloc[0:0]

    G = build_graph(data, raio_km) if len(data) >= 2 else None
    col, _ = colorir_greedy(G) if G is not None else ({}, 0)

    edge_group = folium.FeatureGroup(name=f'Conexões (≤ {raio_km:g}km)', show=True)
    if G is not None:
        for u, v in G.edges():
            lat1, lon1 = G.nodes[u]['pos']
            lat2, lon2 = G.nodes[v]['pos']
            folium.PolyLine([[lat1, lon1], [lat2, lon2]],
                             weight=1.5, color='#40916c', opacity=0.45).add_to(edge_group)
    edge_group.add_to(m)

    node_group = folium.FeatureGroup(name='Estabelecimentos', show=True)
    for _, r in data.iterrows():
        lat, lon = r['coord']
        cor_idx = col.get(r['Nome'], None)
        cor_hex = CHROM_PALETTE[cor_idx % len(CHROM_PALETTE)] if cor_idx is not None else '#adb5bd'
        isolado = G is not None and G.degree(r['Nome']) == 0
        popup = (
            f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:200px'>"
            f"<b style='color:#1b4332'>{r['Nome']}</b><br>"
            f"<span style='color:#2d6a4f'>Bairro:</span> {r['Bairro']}<br>"
            f"<span style='color:#2d6a4f'>Categoria:</span> {r['Categoria']}<br>"
            f"<span style='color:#2d6a4f'>Grau (raio {raio_km:g}km):</span> "
            f"{G.degree(r['Nome']) if G is not None else 0}<br>"
            + ("<span style='color:#e76f51'><b>Isolado neste raio</b></span><br>" if isolado else "")
            + f"<span style='color:#2d6a4f'>Grupo cromático:</span> {cor_idx if cor_idx is not None else 'N/A'}"
            f"</div>"
        )
        folium.CircleMarker(
            [lat, lon], radius=9 if isolado else 7,
            color='#e76f51' if isolado else 'white', weight=2 if isolado else 1.5,
            fill=True, fill_color=cor_hex, fill_opacity=0.9,
            popup=folium.Popup(popup, max_width=280), tooltip=r['Nome'],
        ).add_to(node_group)
    node_group.add_to(m)

    # Destaque da Policlínica (CNES 2453908)
    poli_row = df_geo[df_geo['Nome'] == POLI_NOME_CSV]
    if not poli_row.empty:
        lat, lon = poli_row.iloc[0]['coord']
        star_group = folium.FeatureGroup(name='★ Policlínica (CNES)', show=True)
        folium.Marker(
            [lat, lon], icon=folium.Icon(color='darkgreen', icon='star', prefix='fa'),
            tooltip=f"★ {POLI_NOME_CSV} (CNES {POLI_CNES})",
            popup=folium.Popup(
                f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:220px'>"
                f"<b style='color:#1b4332'>★ {POLI_NOME_CSV}</b><br>"
                f"<span style='color:#2d6a4f'>CNES:</span> {POLI_CNES}<br>"
                f"<i>Ver detalhes na aba \"Lista de Estabelecimentos\"</i></div>", max_width=300),
        ).add_to(star_group)
        star_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m._repr_html_()


def layout():
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Filtros", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px',
                    'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'marginBottom': '16px',
                }),
                html.Label("Categoria de Serviço", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Checklist(
                    id='map-cat',
                    options=[{'label': f" {c}", 'value': c} for c in ALL_CATS],
                    value=ALL_CATS,
                    style={'marginTop': '8px', 'marginBottom': '16px',
                           'fontSize': '0.84rem', 'color': C['txt2'],
                           'display': 'flex', 'flexDirection': 'column', 'gap': '4px'},
                ),
                html.Label("Raio de proximidade (conexões)", style={
                    'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.RadioItems(
                    id='map-raio',
                    options=[{'label': f' {r:g} km', 'value': r} for r in RADII_KM],
                    value=2.0, inline=False,
                    inputStyle={'marginRight': '6px'},
                    style={'marginTop': '8px', 'marginBottom': '20px', 'color': C['txt2'],
                           'display': 'flex', 'flexDirection': 'column', 'gap': '6px', 'fontSize': '0.86rem'},
                ),
                html.H4("Resumo", style={'color': C['primary'], 'borderBottom': f"1px solid {C['light']}",
                                         'paddingBottom': '8px', 'marginTop': '0'}),
                html.Div(id='map-summary'),
                html.H4("Legenda de categorias", style={'color': C['primary'], 'marginTop': '20px',
                                          'borderBottom': f"1px solid {C['light']}", 'paddingBottom': '8px'}),
                html.Div([
                    html.Div([
                        html.Div(style={'width': '13px', 'height': '13px', 'backgroundColor': col,
                                        'marginRight': '8px', 'flexShrink': '0'}),
                        html.Span(cat, style={'fontSize': '0.8rem', 'color': C['txt2']}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'})
                    for cat, col in CAT_COLORS.items()
                ]),
            ], style={'width': '270px', 'flexShrink': '0', 'backgroundColor': C['white'],
                      'border': f"1px solid {C['line']}", 'borderRadius': '14px 0 0 14px',
                      'padding': '20px', 'overflowY': 'auto'},
               role='region', **{'aria-label': 'Filtros do mapa'}),

            html.Div([
                html.Iframe(id='map-frame', srcDoc='', title='Mapa interativo de estabelecimentos de saúde',
                            style={'width': '100%', 'height': '100%', 'border': 'none'}),
            ], style={'flex': '1', 'height': '620px', 'border': f"1px solid {C['line']}",
                      'borderLeft': 'none', 'borderRadius': '0 14px 14px 0', 'overflow': 'hidden',
                      'backgroundColor': C['white']}),
        ], style={'display': 'flex', 'marginBottom': '12px', 'height': '620px',
                  'boxShadow': '0 8px 24px rgba(27,67,50,0.06)', 'borderRadius': '14px'}),
        html.P(
            "Marcadores com borda vermelha destacada indicam estabelecimentos isolados no raio "
            "selecionado (sem nenhum vizinho ≤ raio). A cor de preenchimento reflete o grupo "
            "cromático (coloração greedy) do grafo naquele raio — não é uma escala de qualidade.",
            style={'color': C['txt2'], 'fontSize': '0.82rem', 'fontStyle': 'italic'},
        ),
    ], style={'padding': '20px 40px', 'maxWidth': '1500px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('map-frame', 'srcDoc'),
        Output('map-summary', 'children'),
        Input('map-cat', 'value'),
        Input('map-raio', 'value'),
    )
    def update_map(cats, raio):
        cats = cats or []
        fdf = df_geo[df_geo['Categoria'].isin(cats)]
        map_html = make_map(cats, raio)

        summary = html.Div([
            html.Div([
                html.Span(str(len(fdf)), style={'fontSize': '2rem', 'fontWeight': '700',
                                                 'color': C['primary'], 'display': 'block'}),
                html.Span("estabelecimentos exibidos", style={'fontSize': '0.78rem', 'color': C['txt2']}),
            ], style={'marginBottom': '10px'}),
            html.Div([
                html.Span(str(fdf['Bairro'].nunique()), style={'fontSize': '1.5rem', 'fontWeight': '700',
                                                                'color': C['secondary'], 'display': 'block'}),
                html.Span("bairros", style={'fontSize': '0.78rem', 'color': C['txt2']}),
            ]),
        ])
        return map_html, summary
