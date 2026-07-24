"""Saúde Informada — Mapeamento e Análise dos Serviços de Saúde Pública em
Caxias-MA via Teoria dos Grafos.

Ponto de entrada da aplicação: monta o layout raiz (header/tabs/footer) e
registra os callbacks de cada aba. A lógica de dados/grafos vive em
data_utils.py e graph_utils.py; o design system em colors.py e
components.py; cada aba é um módulo próprio em tabs/.
"""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, html

from components import TAB_ACTIVE_STYLE, TAB_STYLE, app_footer, app_header
from tabs import (
    tab_case_study,
    tab_coverage,
    tab_education,
    tab_gaps,
    tab_graphs,
    tab_map,
    tab_overview,
    tab_scenarios,
)

app = dash.Dash(
    __name__,
    title="Saúde Informada (Caxias-MA)",
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
)
server = app.server

TABS = [
    ('overview',    'Visão Geral',                 tab_overview),
    ('mapa',        'Mapa Interativo',              tab_map),
    ('grafos',      'Análise de Grafos',            tab_graphs),
    ('cobertura',   'Cobertura por Bairro',         tab_coverage),
    ('vazios',      'Vazios Assistenciais',         tab_gaps),
    ('educativo',   'Módulo Educativo (SUS)',       tab_education),
    ('cenarios',    'Cenários "E se?"',             tab_scenarios),
    ('policlinica', 'Estudo de Caso - Policlínica', tab_case_study),
]

app.layout = html.Div([
    app_header(),

    dbc.Tabs(id='tabs', active_tab=TABS[0][0], children=[
        dbc.Tab(label=label, tab_id=value,
                tab_style=TAB_STYLE, active_tab_style=TAB_ACTIVE_STYLE,
                label_style={'color': 'inherit'}, active_label_style={'color': 'inherit'})
        for value, label, _ in TABS
    ], style={'backgroundColor': '#ffffff', 'borderBottom': '1px solid #e3efe8',
              'position': 'sticky', 'top': '0', 'zIndex': '999',
              'boxShadow': '0 2px 12px rgba(27,67,50,0.06)'}),

    dbc.Spinner(html.Div(id='content'), color='success', delay_show=200),

    app_footer(),
], style={'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif',
          'background': 'transparent', 'minHeight': '100vh'})


@app.callback(Output('content', 'children'), Input('tabs', 'active_tab'))
def render_tab(tab_value):
    for value, _, module in TABS:
        if value == tab_value:
            return module.layout()
    return html.Div()


for _, _, module in TABS:
    if hasattr(module, 'register_callbacks'):
        module.register_callbacks(app)


if __name__ == '__main__':
    app.run(debug=True)
