"""Aba 2 — Mapa Interativo.

Mapa Folium com filtros por categoria/tipo/busca, slider de raio de
proximidade (1-5 km, controla a camada de conexões do grafo), clustering
de marcadores e camada de heatmap de densidade.
"""
import folium
from dash import Input, Output, dcc, html
from folium import plugins

from colors import C, CAT_COLORS, MAP_CENTER
from components import card
from data_utils import POLI_CNES, POLI_NOME, TOTAL_H_MEDICAS, N_ESPECIALIDADES, df
from graph_utils import build_graph, coloring

all_cats = sorted(df['Categoria'].unique())


def make_map(cats=None, tipo_filter='Todos', busca='', raio_km=1.0,
             cluster=False, heatmap=False):
    m = folium.Map(location=list(MAP_CENTER), zoom_start=13, tiles="CartoDB positron")
    data = df.copy()
    if cats is not None:
        data = data[data['Categoria'].isin(cats)]
    if tipo_filter != 'Todos':
        data = data[data['Tipo'] == tipo_filter]
    if busca:
        data = data[data['Nome'].str.contains(busca, case=False, na=False) |
                    data['Categoria'].str.contains(busca, case=False, na=False)]
    node_set = set(data['Nome'])

    # control=False: a filtragem por categoria acontece no Dash (checklist),
    # que refaz o mapa filtrando nós E arestas juntos — o LayerControl do
    # folium só esconderia os marcadores, deixando as arestas órfãs.
    feature_groups = {}
    for cat in data['Categoria'].unique():
        feature_groups[cat] = folium.FeatureGroup(name=cat, show=True, control=False)

    marker_target = {}
    if cluster:
        cluster_group = plugins.MarkerCluster(name='Clusters')
        for cat in feature_groups:
            marker_target[cat] = cluster_group
    else:
        marker_target = feature_groups
        cluster_group = None

    edge_group = folium.FeatureGroup(name=f'Conexões (arestas ≤ {raio_km:g}km)', show=False)

    for _, r in data.iterrows():
        lat, lon = r['coord']
        cat = r['Categoria']
        tipo = r['Tipo']
        tipo_color = '#e76f51' if tipo == 'Emergencial' else '#2d6a4f'
        popup = (
            f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:200px'>"
            f"<b style='color:#1b4332'>{r['Nome']}</b><br>"
            f"<span style='color:#2d6a4f'>Bairro:</span> {r['Bairro']}<br>"
            f"<span style='color:#2d6a4f'>Categoria:</span> {cat}<br>"
            f"<span style='color:#2d6a4f'>Tipo:</span> "
            f"<b style='color:{tipo_color}'>{tipo}</b><br>"
            f"<span style='color:#2d6a4f'>Cor cromática:</span> {coloring.get(r['Nome'], 'N/A')}"
            f"</div>"
        )
        folium.CircleMarker(
            [lat, lon], radius=8, color='white', weight=1.5, fill=True,
            fill_color=CAT_COLORS.get(cat, '#2d6a4f'), fill_opacity=0.9,
            popup=folium.Popup(popup, max_width=280), tooltip=r['Nome'],
        ).add_to(marker_target[cat])

    # Conexões recalculadas para o raio de proximidade selecionado no slider
    Gr = build_graph(data, threshold=raio_km) if len(data) >= 2 else None
    if Gr is not None:
        for u, v in Gr.edges():
            if u in node_set and v in node_set:
                lat1, lon1 = Gr.nodes[u]['pos']
                lat2, lon2 = Gr.nodes[v]['pos']
                folium.PolyLine([[lat1, lon1], [lat2, lon2]],
                                 weight=1.5, color='#40916c', opacity=0.4).add_to(edge_group)

    if heatmap and len(data):
        heat_group = folium.FeatureGroup(name='Mapa de Calor (densidade)', show=True)
        plugins.HeatMap([[r['coord'][0], r['coord'][1]] for _, r in data.iterrows()],
                         radius=18, blur=22).add_to(heat_group)
        heat_group.add_to(m)

    edge_group.add_to(m)
    if cluster_group is not None:
        cluster_group.add_to(m)
    else:
        for fg in feature_groups.values():
            fg.add_to(m)

    # Destaque do estudo de caso (CNES 2453908)
    poli_row = df[df['Nome'] == POLI_NOME]
    if not poli_row.empty:
        lat, lon = poli_row.iloc[0]['coord']
        star_group = folium.FeatureGroup(name='★ Estudo de Caso da Policlínica', show=True)
        folium.Marker(
            [lat, lon], icon=folium.Icon(color='darkgreen', icon='star', prefix='fa'),
            tooltip=f"★ {POLI_NOME} (CNES {POLI_CNES}) Estudo de Caso",
            popup=folium.Popup(
                f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:220px'>"
                f"<b style='color:#1b4332'>★ {POLI_NOME}</b><br>"
                f"<span style='color:#2d6a4f'>CNES:</span> {POLI_CNES}<br>"
                f"<span style='color:#2d6a4f'>Tipo:</span> Policlínica · Média Complexidade<br>"
                f"<span style='color:#2d6a4f'>Horas médicas:</span> {TOTAL_H_MEDICAS}h/sem · "
                f"{N_ESPECIALIDADES} especialidades<br>"
                f"<i>Ver aba \"Estudo de Caso - Policlínica\"</i></div>", max_width=300),
        ).add_to(star_group)
        star_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    plugins.Fullscreen().add_to(m)
    return m._repr_html_()


def layout():
    return html.Div([
        html.Div([
            # Sidebar de filtros
            html.Div([
                html.H3("Filtros", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px',
                    'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'marginBottom': '16px',
                }),
                html.Label("Buscar unidade", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Input(
                    id='map-busca', type='text', debounce=True,
                    placeholder='ex.: UBS, CAPS, oftalmo…',
                    style={'width': '100%', 'padding': '7px 10px', 'marginTop': '8px',
                           'marginBottom': '16px', 'border': f"1px solid {C['line']}",
                           'fontSize': '0.86rem', 'boxSizing': 'border-box'},
                ),
                html.Label("Categoria de Serviço", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Checklist(
                    id='map-cat',
                    options=[{'label': f" {c}", 'value': c} for c in all_cats],
                    value=all_cats,
                    style={'marginTop': '8px', 'marginBottom': '16px',
                           'fontSize': '0.84rem', 'color': C['txt2'],
                           'display': 'flex', 'flexDirection': 'column', 'gap': '4px'},
                ),
                html.Label("Tipo de Atendimento", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Dropdown(
                    id='map-tipo',
                    options=[
                        {'label': 'Todos', 'value': 'Todos'},
                        {'label': 'Emergencial', 'value': 'Emergencial'},
                        {'label': 'Não-Emergencial', 'value': 'Não-Emergencial'},
                    ],
                    value='Todos', clearable=False, style={'marginTop': '8px', 'marginBottom': '20px'},
                ),
                html.Label("Raio de proximidade (conexões)", style={
                    'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Slider(id='map-raio', min=1, max=5, step=1, value=1,
                           marks={i: f'{i}km' for i in range(1, 6)},
                           tooltip={'placement': 'bottom', 'always_visible': False}),
                dcc.Checklist(
                    id='map-camadas',
                    options=[
                        {'label': ' Agrupar marcadores (clustering)', 'value': 'cluster'},
                        {'label': ' Mapa de calor (densidade)', 'value': 'heatmap'},
                    ],
                    value=[], style={'marginTop': '16px', 'marginBottom': '16px',
                                     'fontSize': '0.84rem', 'color': C['txt2'],
                                     'display': 'flex', 'flexDirection': 'column', 'gap': '6px'},
                ),
                html.H4("Resumo", style={'color': C['primary'], 'borderBottom': f"1px solid {C['light']}",
                                         'paddingBottom': '8px', 'marginTop': '0'}),
                html.Div(id='map-summary'),
                html.H4("Legenda", style={'color': C['primary'], 'marginTop': '20px',
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

            # Mapa
            html.Div([
                html.Iframe(id='map-frame', srcDoc='', title='Mapa interativo de unidades de saúde',
                            style={'width': '100%', 'height': '100%', 'border': 'none'}),
            ], style={'flex': '1', 'height': '620px', 'border': f"1px solid {C['line']}",
                      'borderLeft': 'none', 'borderRadius': '0 14px 14px 0', 'overflow': 'hidden',
                      'backgroundColor': C['white']}),
        ], style={'display': 'flex', 'marginBottom': '20px', 'height': '620px',
                  'boxShadow': '0 8px 24px rgba(27,67,50,0.06)', 'borderRadius': '14px'}),
    ], style={'padding': '20px 40px', 'maxWidth': '1500px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('map-frame', 'srcDoc'),
        Output('map-summary', 'children'),
        Input('map-cat', 'value'),
        Input('map-tipo', 'value'),
        Input('map-busca', 'value'),
        Input('map-raio', 'value'),
        Input('map-camadas', 'value'),
    )
    def update_map(cats, tipo, busca, raio, camadas):
        busca = (busca or '').strip()
        cats = cats or []
        camadas = camadas or []
        fdf = df[df['Categoria'].isin(cats)]
        if tipo != 'Todos':
            fdf = fdf[fdf['Tipo'] == tipo]
        if busca:
            fdf = fdf[fdf['Nome'].str.contains(busca, case=False, na=False) |
                      fdf['Categoria'].str.contains(busca, case=False, na=False)]

        map_html = make_map(cats, tipo, busca, raio_km=raio,
                             cluster='cluster' in camadas, heatmap='heatmap' in camadas)

        tipo_badge = None
        if tipo != 'Todos':
            badge_color = C['danger'] if tipo == 'Emergencial' else C['secondary']
            tipo_badge = html.Div(tipo, style={
                'backgroundColor': badge_color, 'color': 'white', 'fontSize': '0.72rem',
                'fontWeight': '600', 'borderRadius': '999px', 'padding': '3px 10px',
                'marginTop': '6px', 'display': 'inline-block'})
        summary = html.Div([
            html.Div([
                html.Span(str(len(fdf)), style={'fontSize': '2rem', 'fontWeight': '700',
                                                 'color': C['primary'], 'display': 'block'}),
                html.Span("unidades", style={'fontSize': '0.78rem', 'color': C['txt2']}),
                tipo_badge,
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
        return map_html, summary
