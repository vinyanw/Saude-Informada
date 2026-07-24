"""Aba 7 — Cenários "E se?".

Simulador de intervenções na rede: adicionar/remover unidades e comparar
métricas (grafo, coloração, acessibilidade, cobertura Voronoi) entre o
cenário atual e o simulado.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, ctx, dcc, html
from haversine import haversine

from colors import C, CAT_COLORS, RAIO_ACESSO_KM, TIPO_SERVICO
from components import card
from data_utils import df
from graph_utils import CENTROIDES, get_metricas_base, metricas_cenario, sugerir_local_ubs
from tabs.tab_graphs import fig_graph_coloring

_scen_label = {'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.85rem',
               'display': 'block', 'marginBottom': '4px', 'marginTop': '10px'}
_scen_input = {'width': '100%', 'padding': '7px 10px', 'border': f"1px solid {C['line']}",
               'fontSize': '0.88rem', 'boxSizing': 'border-box'}


def scenario_df(mods):
    """Aplica as modificações do cenário (adições/remoções) ao dataset base."""
    mods = mods or {'add': [], 'remove': []}
    data = df[~df['Nome'].isin(mods.get('remove', []))].copy()
    for a in mods.get('add', []):
        coord = (float(a['lat']), float(a['lon']))
        bairro = min(CENTROIDES.index, key=lambda b: haversine(coord, CENTROIDES[b]))
        novo = {'Nome': a['nome'], 'Bairro': bairro, 'Categoria': a['cat'], 'coord': coord,
                'Tipo': TIPO_SERVICO.get(a['cat'], 'Não-Emergencial')}
        data = pd.concat([data, pd.DataFrame([novo])], ignore_index=True)
    return data


def fig_scen_map(data, added=()):
    """Mapa de seleção do cenário: unidades atuais + grade clicável para
    capturar coordenadas de novas unidades."""
    fig = go.Figure()
    glon = np.linspace(-43.45, -43.27, 46)
    glat = np.linspace(-4.95, -4.80, 38)
    gx, gy = np.meshgrid(glon, glat)
    fig.add_trace(go.Scatter(
        x=gx.ravel(), y=gy.ravel(), mode='markers', marker=dict(size=13, color='rgba(0,0,0,0)'),
        hovertemplate='Lat %{y:.5f} · Lon %{x:.5f}<br><i>clique para usar estas coordenadas</i><extra></extra>',
        showlegend=False,
    ))
    seen = set()
    for r in data.itertuples():
        is_new = r.Nome in added
        fig.add_trace(go.Scatter(
            x=[r.coord[1]], y=[r.coord[0]], mode='markers',
            marker=dict(size=16 if is_new else 9, symbol='star' if is_new else 'circle',
                        color='#e9c46a' if is_new else CAT_COLORS.get(r.Categoria, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{'★ ' if is_new else ''}{r.Nome}</b><br>{r.Categoria} - {r.Bairro}"],
            hovertemplate='%{text}<extra></extra>',
            name='★ Novas (cenário)' if is_new else r.Categoria,
            legendgroup='novo' if is_new else r.Categoria,
            showlegend=(('novo' if is_new else r.Categoria) not in seen),
        ))
        seen.add('novo' if is_new else r.Categoria)
    fig.update_layout(
        title=dict(text='Clique no mapa para capturar lat/lon · área urbana de Caxias',
                   font=dict(size=12, color=C['primary'])),
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9', range=[-43.45, -43.27]),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9', range=[-4.95, -4.80], scaleanchor='x', scaleratio=1),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', hovermode='closest',
        legend=dict(font=dict(size=9), x=1.01, y=1), margin=dict(l=50, r=150, t=40, b=40),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


def _delta(base, novo, fmt='{:.0f}', melhor='maior'):
    d = novo - base
    if abs(d) < 1e-9:
        return html.Span(' -', style={'color': C['txt2'], 'fontSize': '0.8rem'})
    bom = (d > 0) if melhor == 'maior' else (d < 0)
    return html.Span(f" {'▲' if d > 0 else '▼'} {fmt.format(abs(d))}",
                     style={'color': C['secondary'] if bom else C['danger'],
                            'fontSize': '0.8rem', 'fontWeight': '700'})


def render_comparacao(mods):
    """Comparação lado a lado: cenário atual × cenário simulado."""
    base = get_metricas_base()
    data = scenario_df(mods)
    cen = metricas_cenario(data)
    added = [a['nome'] for a in (mods or {}).get('add', [])]
    removed = (mods or {}).get('remove', [])

    linhas = [
        ('Unidades na rede', base['n'], cen['n'], '{:.0f}', 'maior'),
        ('UBS ativas', base['ubs'], cen['ubs'], '{:.0f}', 'maior'),
        ('Arestas (conflitos de proximidade)', base['arestas'], cen['arestas'], '{:.0f}', 'menor'),
        ('Número cromático χ (grupos p/ escalonamento)', base['chi'], cen['chi'], '{:.0f}', 'menor'),
        ('Grau médio do grafo', base['grau_medio'], cen['grau_medio'], '{:.2f}', 'menor'),
        (f'Índice de acessibilidade (% pop ≤ {RAIO_ACESSO_KM:g}km de UBS)',
         base['acess'], cen['acess'], '{:.1f}pp', 'maior'),
        ('Média de habitantes por UBS (Voronoi)', base['hab_ubs'], cen['hab_ubs'], '{:.0f}', 'menor'),
        ('UBS sobrecarregadas (> 4.000 hab)', base['sobrecarga'], cen['sobrecarga'], '{:.0f}', 'menor'),
    ]

    def _cell(v, fmt):
        return fmt.replace('pp', '').format(v)

    tab_cmp = html.Table([
        html.Thead(html.Tr([
            html.Th(h, style={'padding': '10px 14px', 'backgroundColor': C['primary'], 'color': 'white',
                              'fontSize': '0.85rem', 'textAlign': 'left' if h == 'Indicador' else 'center'})
            for h in ['Indicador', 'Cenário Atual', 'Cenário Simulado', 'Variação']
        ])),
        html.Tbody([
            html.Tr([
                html.Td(nome, style={'padding': '8px 14px', 'fontSize': '0.86rem', 'color': C['txt']}),
                html.Td(_cell(b, f), style={'padding': '8px 14px', 'textAlign': 'center',
                                            'fontWeight': '600', 'color': C['txt2']}),
                html.Td(_cell(n, f), style={'padding': '8px 14px', 'textAlign': 'center',
                                            'fontWeight': '700', 'color': C['primary']}),
                html.Td(_delta(b, n, f, m), style={'padding': '8px 14px', 'textAlign': 'center'}),
            ], style={'backgroundColor': 'white' if i % 2 == 0 else C['bg'],
                      'borderBottom': f"1px solid {C['lighter']}"})
            for i, (nome, b, n, f, m) in enumerate(linhas)
        ]),
    ], style={'width': '100%', 'borderCollapse': 'collapse'})

    def _alert_list(alertas):
        if not alertas:
            return html.P("Nenhuma UBS acima do parâmetro da PNAB.",
                          style={'color': C['secondary'], 'fontSize': '0.85rem'})
        return html.Ul([
            html.Li([html.Strong(a['nome'], style={'color': C['danger'] if a['nivel'] == 'danger' else '#9a7b00'}),
                     html.Span(f" - {a['texto']}", style={'color': C['txt2']})],
                    style={'fontSize': '0.83rem', 'marginBottom': '6px'})
            for a in alertas
        ], style={'paddingLeft': '18px', 'margin': '0'})

    sug = sugerir_local_ubs(data)
    sug_div = html.Div([
        html.H4("Facility Location - Onde abrir a próxima UBS?", style={'color': C['primary'], 'marginTop': '0'}),
        (html.P([
            f"Sugestão (greedy, maximiza população coberta a ≤ {RAIO_ACESSO_KM:g}km): instalar UBS em ",
            html.Strong(sug['bairro']),
            f" (lat {sug['coord'][0]:.5f}, lon {sug['coord'][1]:.5f}) - cobriria ",
            html.Strong(f"{sug['ganho']:,} habitantes".replace(',', '.')),
            f" hoje descobertos. Bairros sem UBS a ≤ {RAIO_ACESSO_KM:g}km: {', '.join(sug['descobertos'])}.",
        ], style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.7', 'margin': '0'})
         if sug else
         html.P(f"Toda a população está a ≤ {RAIO_ACESSO_KM:g}km de uma UBS neste cenário - nenhuma "
                "instalação adicional necessária pelo critério de acessibilidade.",
                style={'color': C['secondary'], 'fontSize': '0.88rem', 'margin': '0'})),
    ], style={**card({'borderLeft': f"4px solid {C['accent']}"})})

    mods_txt = []
    if added:
        mods_txt.append(f"Adicionadas: {', '.join(added)}.")
    if removed:
        mods_txt.append(f"Removidas: {', '.join(removed)}.")

    return html.Div([
        html.P(' '.join(mods_txt) or 'Nenhuma modificação - cenário idêntico ao atual.',
               style={'color': C['primary'], 'fontWeight': '600', 'fontSize': '0.9rem'}),
        html.Div(tab_cmp, style=card()),
        html.Div([
            html.Div([
                html.H4("Grafo - Cenário Atual", style={'color': C['primary'], 'marginTop': '0'}),
                dcc.Graph(figure=fig_graph_coloring(base['G'], base['col'], 1.0, True),
                          config={'displayModeBar': False}, style={'height': '420px'}),
                html.H5("Alertas de sobrecarga", style={'color': C['primary'], 'marginBottom': '6px'}),
                _alert_list(base['alertas']),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'marginBottom': '0'})}),
            html.Div([
                html.H4("Grafo - Cenário Simulado", style={'color': C['primary'], 'marginTop': '0'}),
                dcc.Graph(figure=fig_graph_coloring(cen['G'], cen['col'], 1.0, True),
                          config={'displayModeBar': False}, style={'height': '420px'}),
                html.H5("Alertas de sobrecarga", style={'color': C['primary'], 'marginBottom': '6px'}),
                _alert_list(cen['alertas']),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),
        sug_div,
    ])


def layout():
    return html.Div([
        html.H2('Análise de Cenários', style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Simule intervenções na rede: adicione uma nova unidade (informe as coordenadas ou "
            "clique no mapa) ou remova unidades existentes. Ao simular, o grafo de proximidade, a "
            "coloração cromática, a cobertura Voronoi e os índices de acessibilidade são "
            "recalculados e comparados lado a lado com o cenário atual.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        dcc.Store(id='scen-mods', data={'add': [], 'remove': []}),

        html.Div([
            html.Div([
                html.H4("➕ Adicionar unidade", style={'color': C['primary'], 'marginTop': '0',
                        'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px'}),
                html.Label("Nome", style=_scen_label),
                dcc.Input(id='scen-nome', type='text', placeholder='ex.: UBS NOVO HORIZONTE', style=_scen_input),
                html.Label("Categoria", style=_scen_label),
                dcc.Dropdown(id='scen-cat', options=[{'label': c, 'value': c} for c in sorted(CAT_COLORS)],
                             value='UBS', clearable=False, style={'fontSize': '0.88rem'}),
                html.Div([
                    html.Div([
                        html.Label("Latitude", style=_scen_label),
                        dcc.Input(id='scen-lat', type='number', placeholder='-4.86', style=_scen_input),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Label("Longitude", style=_scen_label),
                        dcc.Input(id='scen-lon', type='number', placeholder='-43.36', style=_scen_input),
                    ], style={'flex': '1'}),
                ], style={'display': 'flex', 'gap': '10px'}),
                html.Button("Adicionar ao cenário", id='btn-scen-add', n_clicks=0, style={
                    'marginTop': '14px', 'width': '100%', 'padding': '10px', 'backgroundColor': C['secondary'],
                    'color': 'white', 'border': 'none', 'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.9rem',
                }),
                html.H4("➖ Remover unidade", style={'color': C['primary'], 'borderBottom': f"1px solid {C['line']}",
                        'paddingBottom': '8px', 'marginTop': '24px'}),
                dcc.Dropdown(id='scen-remove-sel', options=[{'label': n, 'value': n} for n in sorted(df['Nome'])],
                             placeholder='Selecione a unidade…', style={'fontSize': '0.85rem'}),
                html.Button("Remover do cenário", id='btn-scen-remove', n_clicks=0, style={
                    'marginTop': '10px', 'width': '100%', 'padding': '10px', 'backgroundColor': C['danger'],
                    'color': 'white', 'border': 'none', 'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.9rem',
                }),
                html.H4("Modificações do cenário", style={'color': C['primary'], 'borderBottom': f"1px solid {C['line']}",
                        'paddingBottom': '8px', 'marginTop': '24px'}),
                html.Div(id='scen-mods-list',
                         children=html.P("Nenhuma modificação.", style={'color': C['txt2'], 'fontSize': '0.84rem'})),
                html.Div([
                    html.Button("Limpar", id='btn-scen-clear', n_clicks=0, style={
                        'flex': '1', 'padding': '10px', 'backgroundColor': C['lighter'], 'color': C['primary'],
                        'border': f"1px solid {C['line']}", 'fontWeight': '600', 'cursor': 'pointer'}),
                    html.Button("▶ Simular Cenário", id='btn-simular', n_clicks=0, style={
                        'flex': '2', 'padding': '10px', 'backgroundColor': C['primary'], 'color': 'white',
                        'border': 'none', 'fontWeight': '700', 'cursor': 'pointer', 'fontSize': '0.95rem'}),
                ], style={'display': 'flex', 'gap': '10px', 'marginTop': '14px'}),
            ], style={**card({'width': '330px', 'flexShrink': '0', 'marginBottom': '0'})}),

            html.Div([
                dcc.Graph(id='scen-map', figure=fig_scen_map(df), config={'displayModeBar': False},
                          style={'height': '640px'}),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'padding': '10px', 'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        dcc.Loading(html.Div(id='scen-result'), type='circle', color=C['primary']),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('scen-lat', 'value'),
        Output('scen-lon', 'value'),
        Input('scen-map', 'clickData'),
        prevent_initial_call=True,
    )
    def scen_click(click_data):
        p = click_data['points'][0]
        return round(p['y'], 6), round(p['x'], 6)

    @app.callback(
        Output('scen-mods', 'data'),
        Output('scen-mods-list', 'children'),
        Output('scen-map', 'figure'),
        Input('btn-scen-add', 'n_clicks'),
        Input('btn-scen-remove', 'n_clicks'),
        Input('btn-scen-clear', 'n_clicks'),
        State('scen-nome', 'value'),
        State('scen-cat', 'value'),
        State('scen-lat', 'value'),
        State('scen-lon', 'value'),
        State('scen-remove-sel', 'value'),
        State('scen-mods', 'data'),
        prevent_initial_call=True,
    )
    def scen_mods_cb(n_add, n_rem, n_clr, nome, cat, lat, lon, remover, mods):
        mods = mods or {'add': [], 'remove': []}
        trig = ctx.triggered_id
        if trig == 'btn-scen-clear':
            mods = {'add': [], 'remove': []}
        elif trig == 'btn-scen-add' and lat is not None and lon is not None:
            nome = (nome or '').strip().upper() or f"NOVA UNIDADE {len(mods['add']) + 1}"
            if nome not in [a['nome'] for a in mods['add']]:
                mods['add'].append({'nome': nome, 'cat': cat or 'UBS', 'lat': float(lat), 'lon': float(lon)})
        elif trig == 'btn-scen-remove' and remover:
            if remover not in mods['remove']:
                mods['remove'].append(remover)

        itens = ([html.Li(f"➕ {a['nome']} ({a['cat']}) @ {a['lat']:.4f}, {a['lon']:.4f}",
                          style={'color': C['secondary'], 'fontSize': '0.82rem', 'marginBottom': '4px'})
                  for a in mods['add']] +
                 [html.Li(f"➖ {r}", style={'color': C['danger'], 'fontSize': '0.82rem', 'marginBottom': '4px'})
                  for r in mods['remove']])
        lista = (html.Ul(itens, style={'paddingLeft': '18px', 'margin': '0'}) if itens
                 else html.P("Nenhuma modificação.", style={'color': C['txt2'], 'fontSize': '0.84rem'}))
        data = scenario_df(mods)
        return mods, lista, fig_scen_map(data, added=[a['nome'] for a in mods['add']])

    @app.callback(
        Output('scen-result', 'children'),
        Input('btn-simular', 'n_clicks'),
        State('scen-mods', 'data'),
        prevent_initial_call=True,
    )
    def simular_cenario(n, mods):
        return render_comparacao(mods)
