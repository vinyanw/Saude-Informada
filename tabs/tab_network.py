"""Aba 3 — Análise da Rede.

Tabela de métricas de conectividade do grafo espacial para cada raio
testado (0.5/1/2/3/5 km) e interpretação cautelosa dos resultados.
A coloração cromática é apresentada como uma leitura entre outras —
nunca como conclusão isolada sobre a qualidade da distribuição.
"""
from dash import Input, Output, dash_table, dcc, html

from colors import C, DEFAULT_RADIUS_KM
from components import card, rec_card
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
        tooltip_header={
            'n_isolados': 'Estabelecimentos sem nenhum vizinho dentro do raio. Candidatos a "possível '
                          'vazio assistencial" — depende do contexto (rural x urbano) e do raio escolhido.',
            'n_componentes': 'Número de agrupamentos desconexos. Muitos componentes pequenos indicam uma '
                             'rede fragmentada nesse raio.',
            'tamanho_maior_componente': 'Nº de vértices no maior agrupamento conexo. Valor próximo do total '
                                        'de vértices sugere concentração geográfica dos serviços.',
            'n_cores_greedy': 'Número mínimo aproximado de cores para que dois estabelecimentos ligados por '
                              'aresta não recebam a mesma cor (heurística greedy). Cresce com a densidade de '
                              'conexões: descreve a estrutura espacial da rede, não a qualidade do atendimento.',
            'n_cores_dsatur': 'Mesma leitura da coloração greedy, por uma heurística diferente (saturação). '
                              'Serve de comparação — não é nota de qualidade clínica.',
        },
        tooltip_delay=0, tooltip_duration=None,
        css=[{'selector': '.dash-table-tooltip',
              'rule': 'max-width: 320px; font-size: 0.8rem; line-height: 1.5;'}],
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


def _diagnosticos(raio_km):
    """Traduz as métricas do raio selecionado em cartões de diagnóstico espacial
    e encaminhamentos investigativos. Heurística cautelosa: os limiares são
    relativos ao total de vértices e o cenário de isolamento persistente é
    sempre avaliado no maior raio testado (independe do raio exibido)."""
    m = metricas_raio(raio_km)
    todos = {r['raio_km']: r for r in get_metricas_todos_raios()}
    raio_max = max(todos)
    m_max = todos[raio_max]
    V = m['n_vertices'] or 1
    cards = []

    # A — isolamento que persiste mesmo no maior raio testado
    if m_max['n_isolados'] >= 3:
        nomes = ', '.join(sorted(m_max['isolados'])[:4])
        extra = ', …' if m_max['n_isolados'] > 4 else ''
        cards.append(rec_card(
            'danger', 'Possível vazio assistencial persistente',
            f"{m_max['n_isolados']} estabelecimentos permanecem sem vizinhos mesmo no maior raio testado "
            f"({raio_max:g} km) — entre eles: {nomes}{extra}. Isso caracteriza um indício de \"possível "
            f"vazio assistencial\", não uma constatação. Encaminhamento sugerido: priorizar estudos "
            f"complementares nessas áreas (população residente, tempo real de deslocamento pelas vias, "
            f"cobertura de equipes de Saúde da Família, sazonalidade de acesso) antes de considerar "
            f"qualquer alternativa de expansão ou reorganização da oferta."))

    # B — isolamento que se resolve ao ampliar o raio
    recuperados = sorted(set(m['isolados']) - set(m_max['isolados']))
    if recuperados:
        nomes = ', '.join(recuperados[:4])
        extra = ', …' if len(recuperados) > 4 else ''
        cards.append(rec_card(
            'warn', 'Cobertura esparsa dependente de escala',
            f"{len(recuperados)} estabelecimento(s) aparecem isolados a {raio_km:g} km mas se conectam em "
            f"raios maiores ({nomes}{extra}). A leitura mais provável é de cobertura existente, porém "
            f"pouco adensada no entorno imediato. Encaminhamento sugerido: avaliar soluções de articulação "
            f"da rede já instalada — transporte sanitário, atendimento itinerante, fluxos de referência — "
            f"em vez de assumir insuficiência de oferta."))

    # C — fragmentação real (agrupamentos com 2+ vértices, descontados os isolados)
    nao_triviais = m['n_componentes'] - m['n_isolados']
    if nao_triviais >= 4:
        cards.append(rec_card(
            'warn', 'Fragmentação da rede no raio analisado',
            f"A {raio_km:g} km, além dos pontos isolados, a rede se divide em {nao_triviais} agrupamentos "
            f"distintos com dois ou mais estabelecimentos, o que sugere sub-redes locais pouco articuladas "
            f"entre si. Não indica, isoladamente, falta de serviços. Encaminhamento sugerido: revisar os "
            f"fluxos de referência e contrarreferência entre os agrupamentos e verificar se a fragmentação "
            f"acompanha barreiras geográficas reais (rios, rodovias, zona rural) ou apenas o parâmetro de "
            f"raio adotado."))

    # D — baixa densidade de arestas / pouca redundância
    if m['grau_medio'] < 4:
        cards.append(rec_card(
            'warn', 'Baixa redundância de proximidade',
            f"O grau médio a {raio_km:g} km é de {m['grau_medio']:.1f}: cada estabelecimento tem poucas "
            f"alternativas próximas. Isso reduz a capacidade da rede de absorver sobrecarga ou "
            f"interrupções pontuais. Encaminhamento sugerido: estudos de capacidade instalada, horários "
            f"de funcionamento e demanda estimada nos pontos de menor grau, para dimensionar a folga real "
            f"do sistema."))

    # E — concentração geográfica (um componente domina a rede)
    if m['tamanho_maior_componente'] / V > 0.80:
        cards.append(rec_card(
            'info', 'Concentração geográfica dos serviços',
            f"A {raio_km:g} km, {m['tamanho_maior_componente']} de {V} estabelecimentos "
            f"({m['tamanho_maior_componente'] / V:.0%}) formam um único agrupamento denso, compatível com "
            f"a área central urbana. Concentração não é sinônimo de excesso: pode acompanhar a "
            f"distribuição da população e da demanda. Encaminhamento sugerido: comparar a densidade de "
            f"serviços com densidade demográfica e indicadores de vulnerabilidade por bairro antes de "
            f"qualquer leitura sobre desequilíbrio na oferta."))

    # F — nenhuma das anteriores
    if not cards:
        cards.append(rec_card(
            'info', 'Configuração sem alertas estruturais relevantes',
            f"A {raio_km:g} km, a rede é majoritariamente conexa, com poucos pontos isolados e baixa "
            f"fragmentação. Não há, pelas métricas de grafo, indício espacial que justifique priorização "
            f"específica. Encaminhamento sugerido: monitoramento periódico à medida que o cadastro de "
            f"estabelecimentos for atualizado."))

    return cards


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
            html.P([
                html.Strong("O que a coloração NÃO avalia. "),
                "A coloração do grafo não mede qualidade clínica nem adequação do atendimento: nada informa "
                "sobre resolutividade, tempo de espera, composição das equipes, infraestrutura, oferta de "
                "procedimentos ou satisfação do usuário. Dois estabelecimentos com a mesma cor apenas não "
                "estão diretamente conectados no raio atual; o número da cor não estabelece ranking, "
                "prioridade ou nota. É uma leitura exclusivamente geográfico-estrutural — aponta "
                "fragmentação ou concentração espacial dos serviços, nada além disso.",
            ], style={'color': C['txt2'], 'lineHeight': '1.7', 'fontSize': '0.9rem',
                      'borderLeft': f"4px solid {C['danger']}", 'paddingLeft': '14px', 'marginTop': '16px'}),
            html.P([
                html.Strong("Fluxo de leitura. "),
                "dados geolocalizados → grafo de proximidade (vértices = unidades; arestas = distância "
                "≤ raio) → métricas de conectividade e coloração → identificação de padrões espaciais "
                "(isolamento, fragmentação, concentração) → interpretação cautelosa, condicionada ao raio e "
                "ao contexto urbano/rural → encaminhamentos, sempre no plano da investigação complementar e "
                "nunca no da determinação de obras ou serviços.",
            ], style={'color': C['txt2'], 'lineHeight': '1.7', 'fontSize': '0.88rem', 'marginTop': '16px',
                      'background': '#f5faf7', 'border': f"1px solid {C['line']}", 'borderRadius': '10px',
                      'padding': '14px 16px'}),
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

        html.Div([
            html.H3("Diagnósticos e encaminhamentos", style={'color': C['primary'], 'marginTop': '0'}),
            html.P(
                "Os cartões abaixo traduzem as métricas de conectividade — para o raio selecionado acima — "
                "em possíveis diagnósticos espaciais e em encaminhamentos de natureza investigativa. São "
                "indícios para priorização de análises, não conclusões sobre necessidade de obras ou "
                "serviços: a plataforma subsidia o planejamento, não o substitui. Toda leitura depende do "
                "raio e deve ser cruzada com dados populacionais, de vulnerabilidade social e de capacidade "
                "instalada antes de qualquer decisão.",
                style={'color': C['txt2'], 'lineHeight': '1.7', 'fontSize': '0.9rem', 'marginBottom': '18px'},
            ),
            html.Div(id='net-recs'),
            html.P(
                "Os encaminhamentos têm caráter técnico-investigativo e destinam-se a orientar a agenda de "
                "estudos. A decisão sobre implantação, realocação ou ampliação de serviços de saúde compete "
                "aos gestores do SUS e depende de instrumentos próprios de planejamento (PDR, PPI, Planos "
                "de Saúde), não contemplados nesta análise.",
                style={'color': C['txt2'], 'fontSize': '0.82rem', 'fontStyle': 'italic', 'marginTop': '16px',
                       'borderTop': f"1px solid {C['line']}", 'paddingTop': '12px'},
            ),
        ], style=card()),
    ], style={'padding': '20px 40px', 'maxWidth': '1300px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('net-isolados', 'children'),
        Output('net-recs', 'children'),
        Input('net-raio', 'value'),
    )
    def _update(raio):
        return _lista_isolados(raio), _diagnosticos(raio)
