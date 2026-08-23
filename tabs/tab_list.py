"""Aba 4 — Lista de Estabelecimentos.

Busca + tabela de estabelecimentos e painel de detalhes: categoria,
localização, estabelecimentos próximos (grafo no raio selecionado) e,
quando o estabelecimento selecionado for a Policlínica de Caxias
(CNES 2453908), o bloco de recursos/carga horária extraído do CNES.
"""
from dash import Input, Output, dash_table, dcc, html
from haversine import haversine

from colors import C, DEFAULT_RADIUS_KM
from components import card
from data_utils import (
    POLI_CNES,
    POLI_EQUIPAMENTOS,
    POLI_INFO,
    POLI_INSTALACOES,
    POLI_NOME_CSV,
    POLI_N_MEDICOS,
    POLI_N_PROFISSIONAIS,
    POLI_RESUMO_ESPECIALIDADES,
    df_all,
)

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'

TABLE_COLS = [
    ('Nome', 'Nome'), ('Bairro', 'Bairro'), ('Categoria', 'Categoria'), ('geo_valid', 'Geolocalizado'),
]


def _tabela(filtro=''):
    d = df_all.copy()
    if filtro:
        d = d[d['Nome'].str.contains(filtro, case=False, na=False) |
              d['Categoria'].str.contains(filtro, case=False, na=False) |
              d['Bairro'].str.contains(filtro, case=False, na=False)]
    d = d.copy()
    d['geo_valid'] = d['geo_valid'].map({True: 'Sim', False: 'Não'})
    return dash_table.DataTable(
        id='list-table',
        data=d[[c for c, _ in TABLE_COLS]].to_dict('records'),
        columns=[{'name': label, 'id': key} for key, label in TABLE_COLS],
        row_selectable='single', selected_rows=[],
        page_size=12, sort_action='native',
        style_table={'overflowX': 'auto', 'width': '100%', 'minWidth': '0'},
        style_header={'backgroundColor': C['primary'], 'color': 'white', 'fontWeight': '600'},
        style_cell={'fontFamily': FONT, 'fontSize': '0.85rem', 'padding': '8px 12px', 'textAlign': 'left',
                    'whiteSpace': 'normal', 'height': 'auto', 'overflowWrap': 'break-word'},
        style_cell_conditional=[{'if': {'column_id': 'Nome'}, 'minWidth': '160px', 'maxWidth': '220px'}],
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']}],
    )


def _proximos(nome, raio_km):
    row = df_all[df_all['Nome'] == nome]
    if row.empty or not row.iloc[0]['geo_valid']:
        return html.P("Sem coordenada válida — não é possível calcular estabelecimentos próximos.",
                       style={'color': C['txt2'], 'fontSize': '0.86rem'})
    origem = row.iloc[0]['coord']
    outros = df_all[(df_all['Nome'] != nome) & df_all['geo_valid']].copy()
    outros['dist_km'] = outros['coord'].apply(lambda c: haversine(origem, c))
    proximos = outros[outros['dist_km'] <= raio_km].sort_values('dist_km')
    if proximos.empty:
        return html.P(f"Nenhum estabelecimento a até {raio_km:g}km — possível vazio assistencial "
                       "nas proximidades (verificar também outros raios na aba Análise da Rede).",
                       style={'color': C['danger'], 'fontSize': '0.86rem'})
    return html.Ul([
        html.Li(f"{r['Nome']} — {r['Categoria']} ({r['dist_km']:.2f}km)", style={'marginBottom': '4px'})
        for _, r in proximos.iterrows()
    ], style={'color': C['txt2'], 'fontSize': '0.86rem', 'paddingLeft': '20px', 'maxHeight': '220px', 'overflowY': 'auto'})


def _bloco_cnes():
    especialidades_rows = [
        {'Especialidade/Função': r['Especialidade'], 'Profissionais': r['n_profissionais'],
         'Carga horária total (h/sem)': r['ch_total']}
        for r in POLI_RESUMO_ESPECIALIDADES
    ]
    return html.Div([
        html.H4(f"★ Ficha CNES {POLI_CNES} — {POLI_INFO['nome_fantasia_cnes']}",
                style={'color': C['primary'], 'marginTop': '0'}),
        html.P(POLI_INFO['tipo'], style={'color': C['txt2'], 'fontSize': '0.86rem'}),
        html.P(POLI_INFO['nivel'], style={'color': C['txt2'], 'fontSize': '0.86rem'}),
        html.P(POLI_INFO['horario'], style={'color': C['txt2'], 'fontSize': '0.86rem'}),

        html.Div([
            html.Div([
                html.Span(str(POLI_N_PROFISSIONAIS), style={'fontSize': '1.6rem', 'fontWeight': '700', 'color': C['primary']}),
                html.Span(" profissionais no quadro", style={'fontSize': '0.8rem', 'color': C['txt2']}),
            ], style={'marginRight': '24px'}),
            html.Div([
                html.Span(str(POLI_N_MEDICOS), style={'fontSize': '1.6rem', 'fontWeight': '700', 'color': C['secondary']}),
                html.Span(" médicos", style={'fontSize': '0.8rem', 'color': C['txt2']}),
            ]),
        ], style={'display': 'flex', 'marginBottom': '14px'}),

        html.H5("Serviços especializados ativos (SUS)", style={'color': C['primary'], 'marginBottom': '6px'}),
        html.Ul([html.Li(s, style={'fontSize': '0.84rem'}) for s in POLI_INFO['servicos']],
                style={'color': C['txt2'], 'paddingLeft': '20px', 'marginBottom': '14px'}),

        html.H5("Profissionais e carga horária por especialidade/função", style={'color': C['primary'], 'marginBottom': '6px'}),
        dash_table.DataTable(
            data=especialidades_rows,
            columns=[{'name': k, 'id': k} for k in ['Especialidade/Função', 'Profissionais', 'Carga horária total (h/sem)']],
            page_size=8, sort_action='native',
            style_table={'overflowX': 'auto', 'width': '100%', 'minWidth': '0'},
            style_header={'backgroundColor': C['secondary'], 'color': 'white', 'fontWeight': '600', 'fontSize': '0.8rem'},
            style_cell={'fontFamily': FONT, 'fontSize': '0.82rem', 'padding': '6px 10px', 'textAlign': 'left',
                        'whiteSpace': 'normal', 'height': 'auto', 'overflowWrap': 'break-word'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']}],
        ),

        html.H5("Equipamentos em uso", style={'color': C['primary'], 'marginTop': '14px', 'marginBottom': '6px'}),
        html.Ul([html.Li(f"{nome} ({qtd})", style={'fontSize': '0.84rem'}) for nome, qtd in POLI_EQUIPAMENTOS],
                style={'color': C['txt2'], 'paddingLeft': '20px', 'marginBottom': '10px'}),

        html.H5("Instalações físicas", style={'color': C['primary'], 'marginBottom': '6px'}),
        html.Ul([html.Li(f"{nome} ({qtd})", style={'fontSize': '0.84rem'}) for nome, qtd in POLI_INSTALACOES],
                style={'color': C['txt2'], 'paddingLeft': '20px', 'marginBottom': '0'}),

        html.P("Fonte: Ficha de Estabelecimento CNES/DATASUS, emitida 28/11/2025.",
               style={'color': C['txt2'], 'fontSize': '0.76rem', 'fontStyle': 'italic', 'marginTop': '14px'}),
    ], style={**card({'borderLeft': f"3px solid {C['warn']}", 'marginTop': '16px'})})


def _painel_detalhe(nome, raio_km):
    row = df_all[df_all['Nome'] == nome]
    if row.empty:
        return html.P("Selecione um estabelecimento na tabela.", style={'color': C['txt2']})
    r = row.iloc[0]
    geo_txt = (f"{r['coord'][0]:.5f}, {r['coord'][1]:.5f}" if r['geo_valid']
               else "Sem geolocalização disponível na coleta")
    blocos = [
        html.H3(r['Nome'], style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '4px'}),
        html.P(f"Bairro: {r['Bairro']} · Categoria: {r['Categoria']}",
               style={'color': C['txt2'], 'marginBottom': '4px'}),
        html.P(f"Coordenada: {geo_txt}", style={'color': C['txt2'], 'marginBottom': '16px', 'fontSize': '0.86rem'}),
        html.H4(f"Estabelecimentos próximos (raio {raio_km:g}km)",
                style={'color': C['primary'], 'marginBottom': '8px'}),
        _proximos(nome, raio_km),
    ]
    if nome == POLI_NOME_CSV:
        blocos.append(_bloco_cnes())
    return html.Div(blocos, style=card())


def layout():
    return html.Div([
        html.H2("Lista de Estabelecimentos", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P("Busque por nome, categoria ou bairro e selecione uma linha para ver os detalhes.",
               style={'color': C['txt2'], 'marginBottom': '20px'}),
        html.Div([
            html.Div([
                dcc.Input(id='list-busca', type='text', debounce=True,
                          placeholder='Buscar por nome, categoria ou bairro…',
                          style={'width': '100%', 'padding': '9px 12px', 'marginBottom': '14px',
                                 'border': f"1px solid {C['line']}", 'fontSize': '0.88rem', 'boxSizing': 'border-box'}),
                html.Div(id='list-table-wrap', children=_tabela()),
            ], style={**card(), 'flex': '3', 'minWidth': '420px'}),
            html.Div([
                html.Label("Raio para \"estabelecimentos próximos\"",
                           style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.86rem'}),
                dcc.RadioItems(
                    id='list-raio',
                    options=[{'label': f' {r:g} km', 'value': r} for r in [0.5, 1.0, 2.0, 3.0, 5.0]],
                    value=DEFAULT_RADIUS_KM, inline=True,
                    inputStyle={'marginLeft': '12px', 'marginRight': '4px'},
                    style={'marginTop': '8px', 'marginBottom': '16px', 'color': C['txt2'], 'fontSize': '0.84rem'},
                ),
                html.Div(id='list-detalhe', children=html.P("Selecione um estabelecimento na tabela.",
                                                              style={'color': C['txt2']})),
            ], style={'flex': '4', 'minWidth': '420px'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}),
    ], style={'padding': '20px 40px', 'maxWidth': '1500px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(Output('list-table-wrap', 'children'), Input('list-busca', 'value'))
    def _filtra(busca):
        return _tabela(busca or '')

    @app.callback(
        Output('list-detalhe', 'children'),
        Input('list-table', 'selected_rows'),
        Input('list-table', 'data'),
        Input('list-raio', 'value'),
    )
    def _detalhe(selected_rows, data, raio):
        if not selected_rows or not data:
            return html.P("Selecione um estabelecimento na tabela.", style={'color': C['txt2']})
        nome = data[selected_rows[0]]['Nome']
        return _painel_detalhe(nome, raio)
