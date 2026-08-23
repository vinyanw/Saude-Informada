"""Aba 3 — Análise da Rede.

Tabela de métricas de conectividade do grafo espacial para cada raio
testado (0.5/1/2/3/5 km) e interpretação cautelosa dos resultados.
A coloração cromática é apresentada como uma leitura entre outras —
nunca como conclusão isolada sobre a qualidade da distribuição.
"""
from dash import Input, Output, dash_table, dcc, html

from colors import C, DEFAULT_RADIUS_KM
from components import card
from data_utils import df_geo
from graph_utils import get_metricas_todos_raios, metricas_raio

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'

COLS = [
    ('raio_km', 'Raio (km)'),
    ('n_vertices', 'Vértices'),
    ('n_arestas', 'Arestas'),
    ('grau_medio', 'Grau médio'),
    ('n_isolados', 'Isolados'),
    ('n_componentes', 'Componentes conexos'),
    ('tamanho_maior_componente', 'Maior componente'),
    ('n_cores_greedy', 'Cores (greedy)'),
    ('n_cores_dsatur', 'Cores (DSATUR aprox.)'),
]


def _tabela_metricas():
    rows = get_metricas_todos_raios()
    data = [{k: (round(r[k], 2) if isinstance(r[k], float) else r[k]) for k, _ in COLS} for r in rows]
    return dash_table.DataTable(
        data=data, columns=[{'name': label, 'id': key} for key, label in COLS],
        style_table={'overflowX': 'auto', 'width': '100%', 'minWidth': '0'},
        style_header={'backgroundColor': C['primary'], 'color': 'white', 'fontWeight': '600', 'fontSize': '0.82rem'},
        style_cell={'fontFamily': FONT, 'fontSize': '0.85rem', 'padding': '10px 12px', 'textAlign': 'center',
                    'whiteSpace': 'normal', 'height': 'auto'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']}],
    )


def _lista_isolados(raio_km):
    m = metricas_raio(raio_km)
    if not m['isolados']:
        return html.P("Nenhum estabelecimento isolado neste raio.",
                       style={'color': C['txt2'], 'fontSize': '0.88rem'})
    itens = []
    for nome in sorted(m['isolados']):
        row = df_geo[df_geo['Nome'] == nome]
        bairro = row.iloc[0]['Bairro'] if not row.empty else '?'
        itens.append(html.Li(f"{nome} — {bairro}", style={'marginBottom': '4px'}))
    return html.Ul(itens, style={'color': C['txt2'], 'fontSize': '0.86rem', 'paddingLeft': '20px',
                                  'columns': '2', 'columnGap': '24px'})


def layout():
    return html.Div([
        html.H2("Análise da Rede", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Métricas de conectividade do grafo espacial (vértices = estabelecimentos com "
            "coordenada válida; arestas = distância haversine ≤ raio) para cada raio testado.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        html.Div([
            html.H3("Métricas por raio", style={'color': C['primary'], 'marginTop': '0'}),
            _tabela_metricas(),
        ], style=card()),

        html.Div([
            html.H3("Como interpretar", style={'color': C['primary'], 'marginTop': '0'}),
            html.P([
                "A ",
                html.Strong("coloração cromática (χ)"),
                " sozinha não indica se a distribuição espacial é boa ou ruim: ela tende a crescer junto "
                "com o número de arestas, então um χ maior a 5km reflete apenas uma rede mais densa, não "
                "uma rede pior. A leitura precisa cruzar coloração com conectividade:",
            ], style={'color': C['txt2'], 'lineHeight': '1.7'}),
            html.Ul([
                html.Li([html.Strong("Vértices isolados"), " — estabelecimentos sem nenhum vizinho dentro "
                         "do raio são candidatos a \"possível vazio assistencial\", mas isso depende do "
                         "contexto (zona rural x urbana) e do raio escolhido."],
                        style={'marginBottom': '8px'}),
                html.Li([html.Strong("Componentes conexos"), " — muitos componentes pequenos e desconexos "
                         "indicam uma rede fragmentada nesse raio, não necessariamente um problema "
                         "assistencial isolado."], style={'marginBottom': '8px'}),
                html.Li([html.Strong("Grau médio e maior componente"), " — grau médio alto com um "
                         "componente dominante grande sugere concentração geográfica de serviços "
                         "(provável área central urbana)."], style={'marginBottom': '0'}),
            ], style={'color': C['txt2'], 'lineHeight': '1.7', 'paddingLeft': '20px'}),
            html.P(
                "Nos dados atuais, os estabelecimentos que permanecem isolados mesmo a 5km — o maior raio "
                "testado — são majoritariamente UBS de povoados/localidades rurais distantes do núcleo "
                "urbano. Isso é consistente com a geografia do município, não uma anomalia de coleta; "
                "ainda assim, indica áreas onde não há redundância de atendimento próximo.",
                style={'color': C['txt2'], 'lineHeight': '1.7', 'fontSize': '0.9rem',
                       'borderLeft': f"4px solid {C['accent']}", 'paddingLeft': '14px', 'marginTop': '16px'},
            ),
        ], style=card()),

        html.Div([
            html.H3("Estabelecimentos isolados por raio", style={'color': C['primary'], 'marginTop': '0'}),
            html.Label("Selecione o raio:", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.86rem'}),
            dcc.RadioItems(
                id='net-raio', options=[{'label': f' {r:g} km', 'value': r}
                                         for r in [0.5, 1.0, 2.0, 3.0, 5.0]],
                value=DEFAULT_RADIUS_KM, inline=True,
                inputStyle={'marginLeft': '16px', 'marginRight': '4px'},
                style={'marginTop': '8px', 'marginBottom': '16px', 'color': C['txt2']},
            ),
            html.Div(id='net-isolados'),
        ], style=card()),
    ], style={'padding': '20px 40px', 'maxWidth': '1300px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(Output('net-isolados', 'children'), Input('net-raio', 'value'))
    def _update(raio):
        return _lista_isolados(raio)
