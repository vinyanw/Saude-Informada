"""Componentes de UI reutilizáveis entre abas: cards, KPIs, cabeçalho/rodapé,
seções de metodologia e botões de exportação. Centraliza o "look" definido
em colors.py para manter consistência visual em toda a aplicação.
"""
from dash import dcc, html
import dash_bootstrap_components as dbc

from colors import C

# ──────────────────────────────────────────────────────────
# ESTILOS DE ABAS (dbc.Tabs)
# ──────────────────────────────────────────────────────────
TAB_STYLE = {
    'padding': '14px 22px', 'fontWeight': '600', 'fontSize': '13.5px',
    'color': C['txt2'], 'border': 'none', 'borderBottom': '3px solid transparent',
    'letterSpacing': '0.01em',
}
TAB_ACTIVE_STYLE = {
    **TAB_STYLE, 'color': C['primary'],
    'borderBottom': f"3px solid {C['accent']}",
    'backgroundColor': 'rgba(82,183,136,0.07)',
}

HDR_STYLE = {
    'background': 'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)',
    'color': C['hdr_txt'],
    'padding': '18px 40px', 'borderBottom': '1px solid rgba(82,183,136,0.45)',
    'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between',
}

FOOTER_STYLE = {
    'background': 'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)',
    'borderTop': '1px solid rgba(82,183,136,0.45)', 'marginTop': '24px',
    'padding': '16px 40px', 'display': 'flex', 'justifyContent': 'space-between',
    'alignItems': 'center', 'fontSize': '0.88rem',
}


# ──────────────────────────────────────────────────────────
# CARD BASE
# ──────────────────────────────────────────────────────────
def card(extra=None):
    """Dict de estilo para um card padrão (fundo branco, sombra suave)."""
    s = {'background': C['white'], 'border': f"1px solid {C['line']}",
         'borderRadius': '14px',
         'boxShadow': '0 1px 2px rgba(27,67,50,0.05), 0 8px 24px rgba(27,67,50,0.06)',
         'padding': '26px 28px', 'marginBottom': '20px'}
    if extra:
        s.update(extra)
    return s


def kpi(value, label, color):
    """Card de KPI: valor grande + label, com barra gradiente e hover elevado."""
    return html.Div([
        html.Div(style={'height': '3px', 'width': '38px', 'borderRadius': '2px',
                        'background': f"linear-gradient(90deg, {color}, {C['accent']})",
                        'margin': '0 auto 14px'}),
        html.Span(str(value), style={'fontSize': '2.3rem', 'fontWeight': '800',
                                     'letterSpacing': '-0.03em', 'lineHeight': '1.1',
                                     'color': color, 'display': 'block'}),
        html.Span(label, style={'fontSize': '0.78rem', 'color': C['txt2'],
                                'display': 'block', 'marginTop': '8px',
                                'lineHeight': '1.45'}),
    ], className='hover-card',
       style={**card({'flex': '1', 'minWidth': '160px', 'textAlign': 'center',
                      'marginBottom': '0'})})


def stat(value, label):
    """Estatística compacta para o hero da Visão Geral (fonte monoespaçada)."""
    return html.Div([
        html.Span(str(value), style={'fontSize': '2.2rem', 'fontWeight': '600', 'color': '#74c69d',
                                     'fontFamily': '"JetBrains Mono", monospace',
                                     'letterSpacing': '-0.02em'}),
        html.Span(f" {label}", style={'color': C['lighter'], 'marginRight': '32px',
                                      'fontSize': '0.9rem', 'letterSpacing': '0.03em'}),
    ])


def step(n, title, text):
    """Passo numerado (usado na seção de metodologia)."""
    return html.Div([
        html.Div(str(n), style={
            'width': '34px', 'height': '34px', 'borderRadius': '10px',
            'background': f"linear-gradient(135deg, {C['primary']}, {C['accent']})",
            'boxShadow': '0 4px 10px rgba(45,106,79,0.25)',
            'color': 'white', 'display': 'flex', 'alignItems': 'center',
            'justifyContent': 'center', 'fontWeight': '700', 'marginBottom': '10px',
        }),
        html.H4(title, style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '8px'}),
        html.P(text, style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6', 'margin': '0'}),
    ], style={
        'flex': '1', 'padding': '16px',
        'borderRight': f"1px solid {C['line']}",
        'minWidth': '200px',
    })


def ack(label, title, sub, border_color):
    """Card de agradecimento/crédito institucional."""
    return html.Div([
        html.Div(label, style={
            'fontWeight': '700', 'fontSize': '1.3rem', 'color': C['primary'],
            'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px',
            'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '10px', 'marginBottom': '8px',
        }),
        html.P(title, style={'fontWeight': '600', 'color': C['primary'], 'marginBottom': '4px'}),
        html.P(sub, style={'fontSize': '0.88rem', 'color': C['txt2'], 'margin': '0'}),
    ], className='hover-card',
       style={**card({'borderTop': f'3px solid {border_color}', 'flex': '1', 'marginBottom': '0'})})


def ref_item(authors, title, rest):
    """Referência bibliográfica em formato ABNT simplificado."""
    return html.P([authors, html.Strong(title), rest],
                  style={'marginBottom': '14px', 'lineHeight': '1.7', 'fontSize': '0.9rem'})


def info_card(titulo, conteudo, border_color):
    """Card informativo com borda lateral colorida (ficha técnica)."""
    return html.Div([
        html.H4(titulo, style={'color': C['primary'], 'marginTop': '0',
                               'borderBottom': f"1px solid {C['line']}",
                               'paddingBottom': '8px', 'marginBottom': '10px'}),
        conteudo,
    ], className='hover-card',
       style={**card({'flex': '1', 'minWidth': '260px',
                      'borderLeft': f'3px solid {border_color}', 'marginBottom': '0'})})


def rec_card(nivel, titulo, texto):
    """Card de recomendação automática, com tag de severidade (CRÍTICO/ATENÇÃO/OBSERVAÇÃO)."""
    border = {'danger': C['danger'], 'warn': C['warn'], 'info': C['accent']}[nivel]
    tag = {'danger': 'CRÍTICO', 'warn': 'ATENÇÃO', 'info': 'OBSERVAÇÃO'}[nivel]
    return html.Div([
        html.Div([
            html.Span(tag, style={
                'backgroundColor': border, 'color': 'white' if nivel != 'warn' else C['txt'],
                'fontSize': '0.68rem', 'fontWeight': '700', 'padding': '3px 10px',
                'borderRadius': '5px', 'letterSpacing': '0.06em',
                'marginRight': '10px', 'flexShrink': '0',
            }),
            html.Strong(titulo, style={'color': C['primary'], 'fontSize': '0.95rem'}),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
        html.P(texto, style={'color': C['txt2'], 'fontSize': '0.87rem',
                             'lineHeight': '1.6', 'margin': '0'}),
    ], className='hover-card',
       style={**card({'borderLeft': f'3px solid {border}', 'marginBottom': '12px',
                      'padding': '16px 20px'})})


def sec_title(txt):
    return html.H3(txt, style={'color': C['primary'], 'marginTop': '0',
                               'borderBottom': f"1px solid {C['line']}",
                               'paddingBottom': '8px', 'marginBottom': '16px'})


def method_section(title, authors, year, source, description, figure=None, graph_id=None):
    """Seção padrão de metodologia: ficha (autor/ano/fonte + descrição) + gráfico."""
    graph_kwargs = dict(figure=figure) if figure is not None else dict(id=graph_id)
    return html.Div([
        html.Div([
            html.H3(title, style={'color': C['primary'], 'margin': '0 0 4px'}),
            html.P(f"{authors} - {source}, {year}", style={
                'color': C['txt2'], 'fontSize': '0.86rem', 'fontStyle': 'italic', 'margin': '0 0 12px',
            }),
            html.P(description, style={
                'color': C['txt2'], 'fontSize': '0.91rem', 'lineHeight': '1.6',
                'borderLeft': f"4px solid {C['accent']}", 'paddingLeft': '14px', 'margin': '0',
            }),
        ], style={
            'backgroundColor': '#f5faf7', 'border': f"1px solid {C['line']}",
            'borderRadius': '10px',
            'padding': '18px 20px', 'marginBottom': '16px',
        }),
        dcc.Graph(config={'displayModeBar': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']},
                  style={'height': '520px'}, **graph_kwargs),
    ], style={**card({'marginBottom': '28px'})})


# ──────────────────────────────────────────────────────────
# HEADER / FOOTER
# ──────────────────────────────────────────────────────────
def app_header():
    return html.Div([
        html.Div([
            html.Span("Saúde Informada", style={
                'fontSize': '1.4rem', 'fontWeight': '700', 'color': C['hdr_txt'],
            }),
            html.Span(" · ", style={'color': C['accent'], 'margin': '0 8px'}),
            html.Span("Caxias-MA", style={'fontSize': '1rem', 'color': C['lighter']}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div([
            html.Span(lbl, style={
                'fontSize': '0.72rem', 'color': C['accent'],
                'border': '1px solid rgba(82,183,136,0.55)', 'borderRadius': '999px',
                'padding': '3px 12px', 'marginLeft': '8px',
                'letterSpacing': '0.08em',
                'background': 'rgba(82,183,136,0.08)',
                'fontFamily': '"JetBrains Mono", monospace',
            }) for lbl in ['IFMA', 'PRPGI', 'SUS']
        ], style={'display': 'flex'}),
    ], style=HDR_STYLE, role='banner', **{'aria-label': 'Cabeçalho Saúde Informada'})


def app_footer():
    return html.Div([
        html.Div("Saúde Informada · IFMA Campus Caxias · PRPGI · 2025–2026",
                 style={'color': C['accent']}),
        html.Div("Dados: CNES/DATASUS · SUS · Coleta primária",
                 style={'color': C['accent'], 'fontSize': '0.83rem'}),
    ], style=FOOTER_STYLE, role='contentinfo', **{'aria-label': 'Rodapé com créditos'})


# ──────────────────────────────────────────────────────────
# EXPORTAÇÃO
# ──────────────────────────────────────────────────────────
def export_csv_button(button_id, download_id, label='⬇ Exportar CSV'):
    """Botão + componente Download prontos para um callback que popula
    `download_id.data` com `dcc.send_data_frame`."""
    return html.Div([
        dbc.Button(label, id=button_id, size='sm', style={
            'backgroundColor': C['primary'], 'border': 'none', 'color': 'white',
            'fontWeight': '600', 'fontSize': '0.82rem',
        }),
        dcc.Download(id=download_id),
    ])
