"""Aba 4 — Cobertura por Bairro.

Tabela interativa (Bairro, População, Nº Unidades, Índice, Status,
Demanda estimada) e gráficos de barra/pizza filtráveis por categoria.
"""
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

from colors import C, CAT_COLORS
from components import card, export_csv_button
from data_utils import DEMANDA, DEMANDA_FONTE, IBGE, POPULATION, POP_CENSO_2022_FALLBACK, POP_OFICIAL, df

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'
all_cats = sorted(df['Categoria'].unique())


def coverage_rows(fdf):
    rows = []
    for bairro, grp in fdf.groupby('Bairro'):
        n_u = len(grp)
        pop = POPULATION.get(bairro, 2000)
        ratio = (n_u / pop) * 1000
        if ratio >= 0.8:
            status = 'Adequada'
        elif ratio >= 0.3:
            status = 'Parcial'
        else:
            status = 'Deficiente'
        dem = DEMANDA.get(bairro, dict(atend=0, ocup=0.0, fila=0))
        rows.append(dict(
            Bairro=bairro, **{'Pop. (IBGE)': pop, 'Unidades': n_u,
            'Índice (unid/1000 hab.)': round(ratio, 3), 'Status': status,
            'Atend./mês': dem['atend'], 'Ocupação (%)': dem['ocup'], 'Fila estimada': dem['fila']},
        ))
    return rows


def fig_bar(fdf):
    bc = fdf.groupby('Bairro').size().reset_index(name='n').nlargest(20, 'n')
    fig = go.Figure(go.Bar(
        x=bc['Bairro'], y=bc['n'], marker_color=C['secondary'],
        hovertemplate='<b>%{x}</b><br>Unidades: %{y}<extra></extra>',
    ))
    fig.update_layout(
        title=dict(text='Unidades por Bairro (Top 20)', font=dict(size=13, color=C['primary'])),
        xaxis=dict(tickangle=-45, gridcolor='#e8f5e9'),
        yaxis=dict(title='Unidades', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        margin=dict(l=40, r=20, t=50, b=120), font=dict(family=FONT, color=C['txt']), showlegend=False,
    )
    return fig


def fig_pie(fdf):
    pc = fdf['Categoria'].value_counts().reset_index()
    pc.columns = ['cat', 'n']
    fig = go.Figure(go.Pie(
        labels=pc['cat'], values=pc['n'], hole=0.4,
        marker=dict(colors=[CAT_COLORS.get(c, C['secondary']) for c in pc['cat']]),
        textinfo='percent', textfont=dict(size=10),
    ))
    fig.update_layout(showlegend=True, paper_bgcolor='white',
                       legend=dict(font=dict(size=10), x=1.0),
                       margin=dict(l=0, r=80, t=0, b=0), font=dict(family=FONT))
    return fig


def _table(rows):
    return dash_table.DataTable(
        id='cov-datatable',
        data=rows,
        columns=[{'name': k, 'id': k} for k in
                 ['Bairro', 'Pop. (IBGE)', 'Unidades', 'Índice (unid/1000 hab.)', 'Status',
                  'Atend./mês', 'Ocupação (%)', 'Fila estimada']],
        sort_action='native', filter_action='native', page_size=15,
        style_header={'backgroundColor': C['primary'], 'color': 'white', 'fontWeight': '600'},
        style_cell={'fontFamily': FONT, 'fontSize': '0.85rem', 'padding': '8px 12px', 'textAlign': 'left'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']},
            {'if': {'filter_query': '{Status} = "Adequada"', 'column_id': 'Status'},
             'backgroundColor': C['secondary'], 'color': 'white', 'fontWeight': '600'},
            {'if': {'filter_query': '{Status} = "Parcial"', 'column_id': 'Status'},
             'backgroundColor': C['warn'], 'color': C['txt'], 'fontWeight': '600'},
            {'if': {'filter_query': '{Status} = "Deficiente"', 'column_id': 'Status'},
             'backgroundColor': C['danger'], 'color': 'white', 'fontWeight': '600'},
            {'if': {'filter_query': '{Ocupação (%)} > 100', 'column_id': 'Ocupação (%)'},
             'color': C['danger'], 'fontWeight': '600'},
            {'if': {'filter_query': '{Fila estimada} > 0', 'column_id': 'Fila estimada'},
             'color': C['danger'], 'fontWeight': '600'},
        ],
    )


def layout():
    rows = coverage_rows(df)
    return html.Div([
        html.H2("Cobertura por Bairro", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            f"População calibrada por dados oficiais do IBGE - Censo 2022: "
            f"{IBGE.get('censo_2022', POP_CENSO_2022_FALLBACK):,} hab · "
            f"Estimativa {IBGE.get('ano_estimativa', '—')}: {POP_OFICIAL:,} hab "
            f"({IBGE['fonte']}). Demanda assistencial: {DEMANDA_FONTE}.".replace(',', '.'),
            style={'fontSize': '0.85rem', 'color': C['txt2'], 'fontStyle': 'italic', 'marginBottom': '20px'},
        ),

        html.Div([
            html.Label("Filtrar por categoria", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
            dcc.Checklist(
                id='cov-cat-filter',
                options=[{'label': f' {c}', 'value': c} for c in all_cats], value=all_cats, inline=True,
                style={'marginTop': '8px', 'fontSize': '0.82rem', 'color': C['txt2'],
                       'display': 'flex', 'flexWrap': 'wrap', 'gap': '4px 14px'},
            ),
        ], style=card()),

        html.Div([
            html.Div([dcc.Graph(id='cov-bar-chart', figure=fig_bar(df), config={'displayModeBar': False},
                                style={'height': '360px'})],
                     style={**card({'flex': '1.6', 'marginRight': '20px', 'padding': '16px', 'marginBottom': '0'})}),
            html.Div([
                html.H4("Distribuição por Categoria", style={'color': C['primary'], 'marginTop': '0'}),
                dcc.Graph(id='cov-pie-chart', figure=fig_pie(df), config={'displayModeBar': False},
                          style={'height': '300px'}),
            ], style={**card({'flex': '1', 'padding': '16px', 'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '20px'}),

        html.Div([
            html.Div([
                html.H3("Tabela de Cobertura", style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '0'}),
                export_csv_button('btn-export-cov', 'dl-cov'),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '14px'}),
            html.Div(id='cov-table', children=_table(rows)),
        ], style=card()),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('cov-bar-chart', 'figure'),
        Output('cov-pie-chart', 'figure'),
        Output('cov-table', 'children'),
        Input('cov-cat-filter', 'value'),
    )
    def update_coverage(cats):
        cats = cats or []
        fdf = df[df['Categoria'].isin(cats)]
        return fig_bar(fdf), fig_pie(fdf), _table(coverage_rows(fdf))

    @app.callback(
        Output('dl-cov', 'data'),
        Input('btn-export-cov', 'n_clicks'),
        prevent_initial_call=True,
    )
    def export_cov(n_clicks):
        import pandas as pd
        rows = coverage_rows(df)
        out = pd.DataFrame(rows)
        return dcc.send_data_frame(out.to_csv, 'cobertura_por_bairro.csv', index=False)
