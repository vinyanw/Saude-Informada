"""Aba 3 — Análise de Grafos.

Visualização do grafo (spring layout + coloração), métricas (χ, grau
médio, componentes conectados, nós isolados), comparação entre
estratégias de coloração (Greedy/DSATUR/Aleatório) e tabela de unidades
por grupo de cor.
"""
import networkx as nx
import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

from colors import C, CHROM_PALETTE, THRESHOLD_KM, THRESHOLDS_KM
from components import card, method_section
from data_utils import POLI_CNES, POLI_NOME, df
from graph_utils import (
    COLORING_STRATEGIES,
    G,
    build_graph,
    chromatic_n,
    coloring,
    isolated_nodes,
)

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'


def _edge_traces(layout, Gr):
    ex, ey = [], []
    for u, v in Gr.edges():
        x1, y1 = layout[u]
        x2, y2 = layout[v]
        ex += [x1, x2, None]
        ey += [y1, y2, None]
    return go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=0.8, color='#b7e4c7'),
                       hoverinfo='none', name='Arestas', showlegend=False)


def fig_graph_coloring(Gr, col, thr, com_pesos=True):
    chi = max(col.values()) + 1 if col else 0
    node_x, node_y, node_col, hover = [], [], [], []
    for n in Gr.nodes():
        lat, lon = Gr.nodes[n]['pos']
        node_x.append(lon); node_y.append(lat)
        c = col.get(n, 0)
        node_col.append(CHROM_PALETTE[c % len(CHROM_PALETTE)])
        hover.append(f"<b>{n}</b><br>Bairro: {Gr.nodes[n]['bairro']}<br>"
                     f"Categoria: {Gr.nodes[n]['categoria']}<br>Cor cromática: {c}")

    ex, ey = [], []
    for u, v in Gr.edges():
        la1, lo1 = Gr.nodes[u]['pos']; la2, lo2 = Gr.nodes[v]['pos']
        ex += [lo1, lo2, None]; ey += [la1, la2, None]

    fig = go.Figure([
        go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=1, color='#95d5b2'),
                   hoverinfo='none', name='Arestas', showlegend=False),
        go.Scatter(x=node_x, y=node_y, mode='markers',
                   marker=dict(size=11, color=node_col, line=dict(width=1.5, color='#1b4332')),
                   text=hover, hovertemplate='%{text}<extra></extra>', name='Unidades'),
    ])
    if POLI_NOME in Gr.nodes:
        plat, plon = Gr.nodes[POLI_NOME]['pos']
        fig.add_trace(go.Scatter(
            x=[plon], y=[plat], mode='markers+text',
            marker=dict(size=22, symbol='star', color='#e9c46a', line=dict(width=2, color='#1b4332')),
            text=['★ Estudo de Caso'], textposition='top center',
            textfont=dict(size=10, color=C['primary']),
            hovertemplate=(f"<b>★ {POLI_NOME}</b><br>CNES {POLI_CNES} (Estudo de Caso)<br>"
                           f"Grau no grafo: {Gr.degree(POLI_NOME)} vizinhos ≤ {thr}km<extra></extra>"),
            showlegend=False,
        ))
    peso_txt = ' · arestas ponderadas por tipo (emergência ×2)' if com_pesos else ''
    fig.update_layout(
        title=dict(text=f'Coloração por Proximidade Geográfica (threshold {thr}km) - nº cromático: {chi}',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', showlegend=False, paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9'),
        margin=dict(l=50, r=30, t=60, b=50), font=dict(family=FONT),
        annotations=[dict(
            text=f"Nós: {Gr.number_of_nodes()} · Arestas: {Gr.number_of_edges()} · Cores: {chi}{peso_txt}",
            xref='paper', yref='paper', x=0, y=-0.13, showarrow=False,
            font=dict(size=11, color=C['secondary']))],
    )
    return fig


def fig_forceatlas2(Gr):
    from colors import CAT_COLORS
    pos = nx.spring_layout(Gr, k=2.2, iterations=120, seed=42)
    traces = [_edge_traces(pos, Gr)]
    seen = set()
    for n in Gr.nodes():
        cat = Gr.nodes[n]['categoria']
        x, y = pos[n]
        traces.append(go.Scatter(
            x=[x], y=[y], mode='markers',
            marker=dict(size=12, color=CAT_COLORS.get(cat, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{n}</b><br>Bairro: {Gr.nodes[n]['bairro']}<br>Categoria: {cat}"],
            hovertemplate='%{text}<extra></extra>', name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text='Rede de Serviços - Layout ForceAtlas2/Spring por Categoria',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1, font=dict(size=10)),
        margin=dict(l=20, r=200, t=60, b=20), font=dict(family=FONT),
    )
    return fig


def fig_centralidade(Gr):
    bet = nx.betweenness_centrality(Gr, weight='distance')
    clo = nx.closeness_centrality(Gr, distance='distance')
    top = sorted(bet, key=bet.get, reverse=True)[:12][::-1]
    fig = go.Figure([
        go.Bar(y=top, x=[bet[n] for n in top], orientation='h', name='Betweenness (ponte)',
               marker_color=C['primary'], hovertemplate='<b>%{y}</b><br>Betweenness: %{x:.3f}<extra></extra>'),
        go.Bar(y=top, x=[clo[n] for n in top], orientation='h', name='Closeness (alcance)',
               marker_color=C['accent'], hovertemplate='<b>%{y}</b><br>Closeness: %{x:.3f}<extra></extra>'),
    ])
    fig.update_layout(
        barmode='group',
        title=dict(text='Centralidade - Hubs Críticos da Rede (top 12 por betweenness)',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(title='Centralidade (ponderada pela distância)', gridcolor='#e8f5e9'),
        yaxis=dict(tickfont=dict(size=9)), paper_bgcolor='white', plot_bgcolor='#f8fffe',
        legend=dict(x=0.65, y=0.05, bgcolor='white', bordercolor=C['light'], borderwidth=1, font=dict(size=10)),
        margin=dict(l=10, r=30, t=50, b=40), font=dict(family=FONT),
    )
    return fig


def fig_scheduling(Gr, col):
    chi = max(col.values()) + 1 if col else 0
    pos = nx.spring_layout(Gr, k=1.8, iterations=100, seed=77)
    traces = [_edge_traces(pos, Gr)]
    for c in range(chi):
        nodes = [n for n, cc in col.items() if cc == c]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode='markers',
            marker=dict(size=12, color=CHROM_PALETTE[c % len(CHROM_PALETTE)],
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{n}</b><br>Grupo {c+1}<br>Categoria: {Gr.nodes[n]['categoria']}" for n in nodes],
            hovertemplate='%{text}<extra></extra>', name=f"Grupo {c + 1}",
        ))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text=f'Coloração para Alocação de Serviços - {chi} grupos sem conflito',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1, font=dict(size=10)),
        margin=dict(l=20, r=160, t=60, b=20), font=dict(family=FONT),
    )
    return fig


def fig_voronoi():
    import numpy as _np
    from scipy.spatial import Voronoi
    from colors import CAT_COLORS
    cx, cy = -43.36, -4.865
    mask = (abs(df['coord'].apply(lambda p: p[1]) - cx) < 0.12) & \
           (abs(df['coord'].apply(lambda p: p[0]) - cy) < 0.12)
    sub = df[mask].reset_index(drop=True)
    if len(sub) < 4:
        sub = df

    pts = _np.array([[r['coord'][1], r['coord'][0]] for _, r in sub.iterrows()])
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
                    fig.add_trace(go.Scatter(x=[p0[0], p1[0]], y=[p0[1], p1[1]], mode='lines',
                                              line=dict(color='#74c69d', width=1.2),
                                              hoverinfo='none', showlegend=False))
    except Exception:
        pass

    seen = set()
    for coord, cat, name in zip(pts, cats, names):
        fig.add_trace(go.Scatter(
            x=[coord[0]], y=[coord[1]], mode='markers',
            marker=dict(size=10, color=CAT_COLORS.get(cat, C['secondary']), line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{name}</b><br>Categoria: {cat}"], hovertemplate='%{text}<extra></extra>',
            name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)

    fig.update_layout(
        title=dict(text='Diagrama de Voronoi - Regiões de Influência por Unidade (área urbana)',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9', scaleanchor='x', scaleratio=1),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', hovermode='closest',
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1, font=dict(size=10)),
        margin=dict(l=50, r=200, t=60, b=50), font=dict(family=FONT),
    )
    return fig


def fig_comparacao_estrategias(Gt):
    """Compara nº cromático obtido por cada estratégia de coloração no
    mesmo grafo — mostra o efeito da heurística de ordenação."""
    resultados = {nome: fn(Gt)[1] for nome, fn in COLORING_STRATEGIES.items()}
    fig = go.Figure(go.Bar(
        x=list(resultados.keys()), y=list(resultados.values()),
        marker_color=[C['primary'], C['accent'], C['warn']],
        text=list(resultados.values()), textposition='outside',
    ))
    fig.update_layout(
        title=dict(text='Número Cromático (χ) por Estratégia de Coloração',
                   font=dict(size=13, color=C['primary'])),
        yaxis=dict(title='χ (menor é melhor)', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', showlegend=False,
        margin=dict(l=40, r=20, t=50, b=40), font=dict(family=FONT),
    )
    return fig


def _tabela_grupos(col):
    """Tabela de unidades por cor/grupo cromático."""
    grupos = {}
    for nome, c in col.items():
        grupos.setdefault(c, []).append(nome)
    rows = [{'Grupo': f'Grupo {c + 1}', 'Unidades no grupo': len(nomes),
             'Exemplos': ', '.join(sorted(nomes)[:4]) + ('…' if len(nomes) > 4 else '')}
            for c, nomes in sorted(grupos.items())]
    return dash_table.DataTable(
        data=rows, columns=[{'name': k, 'id': k} for k in ['Grupo', 'Unidades no grupo', 'Exemplos']],
        page_size=10, sort_action='native',
        style_header={'backgroundColor': C['primary'], 'color': 'white', 'fontWeight': '600'},
        style_cell={'fontFamily': FONT, 'fontSize': '0.85rem', 'padding': '8px 12px', 'textAlign': 'left'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']}],
    )


def layout():
    ncomp = nx.number_connected_components(G)
    isolados = isolated_nodes(G)
    return html.Div([
        html.H2("Análise de Grafos", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Metodologias de abstração e visualização aplicadas à rede de serviços de Caxias-MA. "
            "Ajuste o raio de proximidade e a ponderação das arestas - os grafos são recalculados automaticamente.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        html.Div([
            component for component in [
                html.Div([
                    html.Div('nós', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                    html.Div(str(G.number_of_nodes()), style={'fontSize': '1.6rem', 'fontWeight': '700', 'color': C['primary']}),
                ], style={**card({'flex': '1', 'minWidth': '140px', 'textAlign': 'center', 'marginBottom': '0'})}),
                html.Div([
                    html.Div('componentes conectados', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                    html.Div(str(ncomp), style={'fontSize': '1.6rem', 'fontWeight': '700', 'color': C['secondary']}),
                ], style={**card({'flex': '1', 'minWidth': '140px', 'textAlign': 'center', 'marginBottom': '0'})}),
                html.Div([
                    html.Div('nós isolados', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                    html.Div(str(len(isolados)), style={'fontSize': '1.6rem', 'fontWeight': '700',
                                                        'color': C['danger'] if isolados else C['accent']}),
                ], style={**card({'flex': '1', 'minWidth': '140px', 'textAlign': 'center', 'marginBottom': '0'})}),
                html.Div([
                    html.Div('grau médio', style={'fontSize': '0.78rem', 'color': C['txt2']}),
                    html.Div(f"{np.mean([d for _, d in G.degree()]):.1f}",
                             style={'fontSize': '1.6rem', 'fontWeight': '700', 'color': C['warn']}),
                ], style={**card({'flex': '1', 'minWidth': '140px', 'textAlign': 'center', 'marginBottom': '0'})}),
            ]
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        html.Div([
            html.Div([
                html.Label("Raio de proximidade (threshold)",
                           style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.RadioItems(
                    id='graf-threshold',
                    options=[{'label': f' {t:g} km', 'value': t} for t in THRESHOLDS_KM],
                    value=THRESHOLD_KM, inline=True,
                    inputStyle={'marginLeft': '16px', 'marginRight': '4px'},
                    style={'marginTop': '8px', 'color': C['txt2']},
                ),
            ], style={'flex': '1', 'minWidth': '260px'}),
            html.Div([
                html.Label("Pesos nas arestas", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Checklist(
                    id='graf-pesos',
                    options=[{'label': ' Ponderar por tipo de serviço '
                                       '(emergência×emergência = 2,0 · mesmo tipo = 1,0 · misto = 0,5)',
                              'value': 'pesos'}],
                    value=['pesos'], style={'marginTop': '8px', 'color': C['txt2'], 'fontSize': '0.86rem'},
                ),
            ], style={'flex': '2', 'minWidth': '300px'}),
            html.Div(id='graf-stats', style={'flex': '1', 'minWidth': '200px', 'textAlign': 'right',
                                             'color': C['primary'], 'fontWeight': '600', 'fontSize': '0.9rem'}),
        ], style={**card({'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'alignItems': 'center'})}),

        method_section(
            "Graph Colouring: A Visual Tour", "Rhyd Lewis", "2026", "arXiv",
            "Arestas conectam unidades dentro do raio selecionado (distância haversine). "
            "Coloração cromática (greedy, largest_first) destaca conflitos de proximidade, "
            "serviços do mesmo tipo muito próximos e complementaridades entre categorias distintas. "
            "Posições dos nós correspondem às coordenadas geográficas reais.",
            graph_id='g-coloring',
        ),

        html.Div([
            html.H3("Comparação entre Estratégias de Coloração", style={'color': C['primary'], 'marginTop': '0'}),
            html.P(
                "Greedy (largest_first) ordena por grau; DSATUR (aproximado) prioriza o vértice com maior "
                "saturação de cores nos vizinhos; Aleatório serve de baseline ingênuo. Estratégias melhores "
                "tendem a produzir números cromáticos menores.",
                style={'color': C['txt2'], 'fontSize': '0.88rem'},
            ),
            dcc.Graph(figure=fig_comparacao_estrategias(G), config={'displayModeBar': False},
                      style={'height': '360px'}),
        ], style=card()),

        html.Div([
            html.H3("Unidades por Grupo de Cor (coloração atual)", style={'color': C['primary'], 'marginTop': '0'}),
            _tabela_grupos(coloring),
        ], style=card()),

        method_section(
            "Health Centers Network Analysis with Gephi and ForceAtlas2", "Dabire et al.", "2025", "Gephi / ForceAtlas2",
            "Layout baseado em força (spring layout como aproximação do ForceAtlas2): a topologia da rede "
            "emerge da estrutura de conexões, independente da posição geográfica. Nós coloridos por categoria "
            "de serviço. A proximidade visual reflete densidade de conexões.",
            graph_id='g-force',
        ),
        method_section(
            "Centralidade em Redes - Identificação de Hubs Críticos", "Freeman; Brandes", "1977/2001", "Análise de Redes Sociais",
            "Betweenness identifica unidades-ponte por onde passam os menores caminhos da rede (a remoção "
            "fragmenta o sistema); closeness mede o alcance médio de cada unidade às demais. Ambas ponderadas "
            "pela distância geográfica - valores altos indicam hubs prioritários para investimento e contingência.",
            graph_id='g-central',
        ),
        method_section(
            "Voronoi Diagrams em Facility Location", "Aurenhammer, Klein & Lee; Okabe et al.", "2000/2013", "Geometria Computacional",
            "Tesselação de Voronoi sobre as coordenadas das unidades da área urbana central de Caxias. Cada "
            "polígono delimita a região de influência natural de uma unidade, onde ela é o serviço geograficamente "
            "mais próximo. Facilita identificação de gaps de cobertura, sobreposição e redundâncias.",
            figure=fig_voronoi(),
        ),
        method_section(
            "Graph Coloring Applied to Service Allocation and Scheduling", "Marx, D.", "2004",
            "Periodica Polytechnica Electrical Engineering",
            "Extensão da coloração ao problema de alocação de recursos: cada grupo de cor representa um "
            "conjunto de unidades que podem operar em um mesmo turno ou receber a mesma categoria de recurso "
            "sem conflito. O número de grupos necessários (χ) varia com o raio de proximidade selecionado acima.",
            graph_id='g-sched',
        ),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('g-coloring', 'figure'),
        Output('g-force', 'figure'),
        Output('g-central', 'figure'),
        Output('g-sched', 'figure'),
        Output('graf-stats', 'children'),
        Input('graf-threshold', 'value'),
        Input('graf-pesos', 'value'),
    )
    def update_grafos(thr, pesos):
        com_pesos = 'pesos' in (pesos or [])
        from graph_utils import colorir
        Gt = build_graph(df, thr, com_pesos)
        col, chi = colorir(Gt)
        stats = html.Div([
            html.Div(f"χ = {chi}", style={'fontSize': '1.6rem', 'fontFamily': '"JetBrains Mono", monospace'}),
            html.Div(f"{Gt.number_of_edges()} arestas · grau médio "
                     f"{np.mean([d for _, d in Gt.degree()]):.1f}",
                     style={'fontSize': '0.8rem', 'color': C['txt2'], 'fontWeight': '400'}),
        ])
        return (fig_graph_coloring(Gt, col, thr, com_pesos), fig_forceatlas2(Gt),
                fig_centralidade(Gt), fig_scheduling(Gt, col), stats)
