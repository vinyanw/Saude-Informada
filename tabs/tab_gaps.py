"""Aba 5 — Vazios Assistenciais & Insights.

Destaque das unidades isoladas no grafo de proximidade, cobertura
populacional por área de influência (Voronoi/vizinho mais próximo) e
recomendações automáticas de expansão da rede.
"""
import plotly.graph_objects as go
from dash import dash_table, dcc, html

from colors import C, PNAB_LIMITE_ATENCAO, PNAB_LIMITE_CRITICO, RAIO_ACESSO_KM, THRESHOLD_KM
from components import card, rec_card
from data_utils import IBGE
from graph_utils import (
    G,
    alertas_sobrecarga,
    df,
    get_metricas_base,
    isolated_nodes,
    pop_voronoi_ubs,
    sugerir_local_ubs,
)

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'


def fig_pop_voronoi():
    """Cobertura populacional robusta: população calibrada pelo IBGE atribuída
    à UBS mais próxima do centroide de cada bairro. Referência: Portaria
    2.436/2017 (~2.000-4.000 pessoas por equipe de atenção básica)."""
    atribuida, bairros_atendidos = pop_voronoi_ubs(df)
    ordem = sorted(atribuida, key=atribuida.get, reverse=True)
    vals = [atribuida[n] for n in ordem]
    cores = [C['danger'] if v > PNAB_LIMITE_CRITICO else C['warn'] if v > PNAB_LIMITE_ATENCAO else C['secondary']
             for v in vals]
    hover = [f"<b>{n}</b><br>Hab. na área de influência: {atribuida[n]:,}".replace(',', '.') +
             f"<br>Bairros: {', '.join(bairros_atendidos[n]) or '-'}" for n in ordem]

    fig = go.Figure(go.Bar(x=ordem, y=vals, marker_color=cores, text=hover,
                            hovertemplate='%{text}<extra></extra>'))
    fig.add_hline(y=PNAB_LIMITE_ATENCAO, line_dash='dash', line_color=C['warn'],
                  annotation_text=f'Limite recomendado por equipe (Portaria 2.436/2017: '
                                  f'{PNAB_LIMITE_ATENCAO:,} hab)'.replace(',', '.'),
                  annotation_font=dict(size=10, color=C['txt2']))
    fig.update_layout(
        title=dict(text=f'Habitantes por UBS (Área de Influência Voronoi) '
                        f'(população {IBGE.get("ano_estimativa", "2022")} · {IBGE["fonte"]})',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(tickangle=-45, gridcolor='#e8f5e9', tickfont=dict(size=9)),
        yaxis=dict(title='Habitantes atribuídos', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', margin=dict(l=50, r=20, t=60, b=160),
        showlegend=False, font=dict(family=FONT),
    )
    return fig


def _tabela_isolados(nomes):
    rows = [{'Unidade': n, 'Bairro': G.nodes[n]['bairro'], 'Categoria': G.nodes[n]['categoria']}
            for n in sorted(nomes)]
    return dash_table.DataTable(
        data=rows, columns=[{'name': k, 'id': k} for k in ['Unidade', 'Bairro', 'Categoria']],
        page_size=10, sort_action='native',
        style_header={'backgroundColor': C['danger'], 'color': 'white', 'fontWeight': '600'},
        style_cell={'fontFamily': FONT, 'fontSize': '0.85rem', 'padding': '8px 12px', 'textAlign': 'left'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']}],
    )


def _recomendacoes():
    cards = []
    sugestao = sugerir_local_ubs(df)
    if sugestao:
        cards.append(rec_card(
            'danger', f"Instalar nova UBS em {sugestao['bairro']}",
            f"{len(sugestao['descobertos'])} bairro(s) estão a mais de {RAIO_ACESSO_KM:g}km de qualquer UBS. "
            f"Uma unidade em {sugestao['bairro']} (lat {sugestao['coord'][0]:.4f}, lon {sugestao['coord'][1]:.4f}) "
            f"traria ~{sugestao['ganho']:,.0f} hab. para dentro do raio de acesso.".replace(',', '.')
        ))
    for alerta in alertas_sobrecarga(df)[:5]:
        cards.append(rec_card(
            alerta['nivel'], f"Sobrecarga em {alerta['nome']}", alerta['texto']
        ))
    isolados = isolated_nodes(G)
    if isolados:
        cards.append(rec_card(
            'warn', f"{len(isolados)} unidade(s) sem vizinhas a ≤ {THRESHOLD_KM:g}km",
            "Essas unidades não têm alternativa próxima de encaminhamento — candidatas a análise de "
            "redundância zero. Considere reforço de transporte/agenda compartilhada com a unidade mais "
            "próxima disponível na aba Mapa Interativo."
        ))
    if not cards:
        cards.append(rec_card('info', "Rede sem alertas críticos no momento",
                               "Nenhuma UBS excede os limites da PNAB e não há bairros descobertos "
                               f"além de {RAIO_ACESSO_KM:g}km de uma UBS."))
    return cards


def layout():
    m = get_metricas_base()
    isolados = isolated_nodes(G)
    return html.Div([
        html.H2("Vazios Assistenciais & Insights", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Panorama de lacunas na rede: unidades sem vizinhas próximas, regiões de influência "
            "populacional por área de Voronoi e recomendações automáticas de expansão/reforço.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        html.Div([
            html.Div([
                html.Div('Nós isolados', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                html.Div(str(len(isolados)), style={'fontSize': '2rem', 'fontWeight': '800',
                                                      'color': C['danger'] if isolados else C['accent']}),
            ], style={**card({'flex': '1', 'minWidth': '160px', 'textAlign': 'center', 'marginBottom': '0'})}),
            html.Div([
                html.Div(f'Acessibilidade a ≤ {RAIO_ACESSO_KM:g}km de UBS', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                html.Div(f"{m['acess']:.1f}%", style={'fontSize': '2rem', 'fontWeight': '800', 'color': C['primary']}),
            ], style={**card({'flex': '1', 'minWidth': '160px', 'textAlign': 'center', 'marginBottom': '0'})}),
            html.Div([
                html.Div('UBS sobrecarregadas (PNAB)', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                html.Div(str(m['sobrecarga']), style={'fontSize': '2rem', 'fontWeight': '800',
                                                       'color': C['danger'] if m['sobrecarga'] else C['accent']}),
            ], style={**card({'flex': '1', 'minWidth': '160px', 'textAlign': 'center', 'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        html.Div([
            html.H3(f"Unidades Isoladas (sem vizinhas a ≤ {THRESHOLD_KM:g}km)", style={'color': C['primary'], 'marginTop': '0'}),
            html.P(
                "Estas unidades não têm nenhuma outra unidade dentro do raio de proximidade — não há "
                "redundância local de atendimento nem oportunidade de escalonamento conjunto.",
                style={'fontSize': '0.86rem', 'color': C['txt2']},
            ),
            _tabela_isolados(isolados) if isolados else html.P(
                "Nenhuma unidade isolada no threshold atual.", style={'color': C['txt2']}),
        ], style=card()),

        html.Div([
            html.H3("Cobertura Populacional por Área de Influência (Voronoi)", style={'color': C['primary'], 'marginTop': '0'}),
            html.P(
                "Cada bairro é atribuído à UBS mais próxima de seu centroide (região de Voronoi). Barras "
                f"acima de {PNAB_LIMITE_ATENCAO:,} habitantes indicam UBS potencialmente sobrecarregadas "
                "segundo o parâmetro da Portaria 2.436/2017 (PNAB).".replace(',', '.'),
                style={'fontSize': '0.88rem', 'color': C['txt2'], 'lineHeight': '1.6'},
            ),
            dcc.Graph(figure=fig_pop_voronoi(), config={'displayModeBar': False},
                      style={'height': '460px'}),
        ], style=card()),

        html.Div([
            html.H3("Recomendações Automáticas", style={'color': C['primary'], 'marginTop': '0'}),
            html.Div(_recomendacoes()),
        ], style=card()),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})
