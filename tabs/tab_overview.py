"""Aba 1 — Visão Geral / Sobre o Projeto.

Introdução, objetivos, metodologia, KPIs principais, glossário de termos
técnicos e links úteis (CNES, Meu SUS Digital, GitHub).
"""
from dash import html

from colors import C, THRESHOLD_KM
from components import ack, card, kpi, ref_item, stat, step
from data_utils import df
from graph_utils import chromatic_n

n_units = len(df)
n_bairros = df['Bairro'].nunique()
n_cats = df['Categoria'].nunique()


def _section_title(txt):
    return html.H3(txt, style={
        'color': C['primary'], 'marginTop': '0',
        'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px',
        'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px',
        'letterSpacing': '-0.01em',
    })


def _hero():
    return html.Div([
        html.H1("Saúde Informada", style={
            'fontSize': '2.6rem', 'fontWeight': '700', 'color': C['hdr_txt'],
            'margin': '0 0 6px',
        }),
        html.H2(
            "Mapeamento e Análise dos Serviços de Saúde Pública em Caxias-MA via Teoria dos Grafos",
            style={'fontSize': '1.15rem', 'fontWeight': '400', 'color': C['lighter'], 'margin': '0 0 16px'},
        ),
        html.P(
            "Plataforma interativa que integra dados geoespaciais validados a algoritmos de coloração de "
            "grafos para revelar padrões de cobertura, redundâncias e lacunas na rede pública de saúde.",
            style={'color': '#b7e4c7', 'maxWidth': '720px', 'lineHeight': '1.7', 'marginBottom': '24px'},
        ),
        html.Div([stat(n_units, 'unidades'), stat(n_bairros, 'bairros'),
                  stat(n_cats, 'categorias'), stat(chromatic_n, 'cores')],
                 style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style={
        'background': ('radial-gradient(ellipse at 85% 10%, rgba(82,183,136,0.16), transparent 55%), '
                       'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)'),
        'padding': '56px 60px',
        'borderBottom': '1px solid rgba(82,183,136,0.45)',
    })


def _kpis():
    return html.Div([
        kpi(n_units, 'Unidades de saúde mapeadas', C['primary']),
        kpi(n_bairros, 'Bairros cobertos', C['secondary']),
        kpi(f"{chromatic_n}", 'Número cromático (χ)', C['warn']),
        kpi(n_cats, 'Categorias de serviço', C['accent']),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '4px'})


def _sobre_objetivos():
    return html.Div([
        html.Div([
            _section_title("Sobre o Projeto"),
            html.P(
                "Esta pesquisa integra dados geoespaciais dos serviços de saúde pública do município "
                "de Caxias-MA a técnicas computacionais de teoria dos grafos. A coloração de grafos, "
                "técnica que atribui rótulos a vértices de modo que nenhum par adjacente compartilhe o "
                "mesmo rótulo, é utilizada para identificar padrões de cobertura, conflitos de "
                "proximidade e complementaridades na rede de atenção à saúde.",
                style={'lineHeight': '1.7', 'color': C['txt2']},
            ),
            html.P(
                "O dataset foi coletado e validado a partir do CNES/DATASUS e verificação in loco via "
                "Google Maps, abrangendo UBS, hospitais, CAPS, UPA, SAMU, centros especializados, "
                "ambulatórios e serviços de diagnóstico do município.",
                style={'lineHeight': '1.7', 'color': C['txt2'], 'marginBottom': '0'},
            ),
        ], style={**card(), 'flex': '1', 'marginRight': '20px'}),

        html.Div([
            _section_title("Objetivos"),
            html.Ul([
                html.Li(t, style={'marginBottom': '8px'}) for t in [
                    "Mapear e catalogar serviços de saúde de Caxias-MA com coordenadas geográficas validadas",
                    f"Modelar a distribuição como grafo de proximidade (threshold {THRESHOLD_KM:g} km)",
                    "Aplicar algoritmos de coloração para análise de conflitos e cobertura",
                    "Identificar gaps e redundâncias na rede de atenção à saúde",
                    "Comparar abordagens distintas de abstração e visualização de redes de saúde",
                    "Disponibilizar visualizações interativas para apoio à gestão em saúde pública",
                ]
            ], style={'lineHeight': '1.8', 'color': C['txt2'], 'paddingLeft': '20px', 'margin': '0'}),
        ], style={**card(), 'flex': '1'}),
    ], style={'display': 'flex', 'flexWrap': 'wrap'})


def _metodologia():
    return html.Div([
        _section_title("Metodologia"),
        html.Div([
            step(1, "Coleta de Dados",
                 "Levantamento geoespacial via CNES/DATASUS e Google Maps. "
                 "Validação manual de coordenadas e categorização por tipo de serviço."),
            step(2, "Construção do Grafo",
                 f"Vértices = unidades de saúde; arestas = proximidade ≤ {THRESHOLD_KM:g}km (haversine). "
                 "Grafo não-direcionado implementado com NetworkX."),
            step(3, "Coloração Cromática",
                 f"Algoritmo greedy (largest_first) determinou número cromático χ = {chromatic_n}. "
                 "Cada cor representa um grupo de serviços sem conflito de adjacência."),
            step(4, "Análise e Visualização",
                 "Diagramas de Voronoi, grafos com force-layout e mapa interativo revelam "
                 "cobertura por bairro, gaps e padrões topológicos da rede."),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style=card())


def _glossario():
    termos = [
        ("Número Cromático (χ)",
         "Menor quantidade de cores necessárias para colorir os vértices de um grafo sem que "
         "dois vértices adjacentes (conectados por uma aresta) recebam a mesma cor. Aqui, indica "
         "quantos grupos de unidades podem operar simultaneamente sem conflito de proximidade."),
        ("Grau de um vértice",
         "Número de arestas conectadas a um vértice — no contexto do projeto, quantas outras "
         "unidades de saúde estão dentro do raio de proximidade (threshold) de uma unidade."),
        ("Distância de Haversine",
         "Fórmula que calcula a distância em linha reta entre dois pontos na superfície de uma "
         "esfera a partir de suas coordenadas de latitude/longitude — usada para medir a "
         "proximidade real entre unidades de saúde."),
        ("Nó isolado",
         "Unidade de saúde sem nenhuma vizinha dentro do raio de proximidade definido — candidata "
         "a vazio assistencial ou área sem redundância de atendimento próximo."),
        ("Diagrama de Voronoi",
         "Tesselação do espaço em regiões (células), cada uma associada a um ponto de referência, "
         "onde todo local dentro da célula está mais próximo daquele ponto do que de qualquer "
         "outro — usada para estimar a área de influência natural de cada unidade."),
        ("Coloração Greedy (gulosa)",
         "Algoritmo que percorre os vértices em uma ordem e atribui a cada um a menor cor ainda "
         "não usada por seus vizinhos já coloridos. Rápido, mas não garante o número cromático "
         "mínimo teórico."),
        ("DSATUR",
         "Heurística de coloração que prioriza, a cada passo, o vértice com maior grau de "
         "saturação (maior número de cores distintas já usadas entre seus vizinhos) — geralmente "
         "produz colorações mais eficientes que a ordem simples por grau."),
        ("Facility location",
         "Classe de problemas de otimização que busca a melhor localização para instalar novos "
         "recursos (ex.: uma nova UBS) de modo a maximizar a cobertura populacional."),
    ]
    return html.Div([
        _section_title("Glossário de Termos"),
        html.Div([
            html.Div([
                html.Strong(termo, style={'color': C['primary'], 'display': 'block', 'marginBottom': '4px'}),
                html.Span(definicao, style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6'}),
            ], style={'flex': '1', 'minWidth': '280px', 'padding': '12px 0',
                       'borderBottom': f"1px solid {C['line']}"})
            for termo, definicao in termos
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '0 24px'}),
    ], style=card())


def _links_uteis():
    links = [
        ("CNES — Cadastro Nacional de Estabelecimentos de Saúde",
         "Consulte a ficha oficial de qualquer unidade de saúde do Brasil.",
         "http://cnes.datasus.gov.br"),
        ("Meu SUS Digital",
         "Aplicativo/portal oficial do Ministério da Saúde para acesso a carteira de vacinação, "
         "histórico de atendimentos e agendamentos no SUS.",
         "https://meusus.saude.gov.br"),
        ("Repositório do Projeto (GitHub)",
         "Código-fonte completo, dados e metodologia do Saúde Informada.",
         "https://github.com"),
    ]
    return html.Div([
        _section_title("Links Úteis"),
        html.Div([
            html.A([
                html.Strong(titulo, style={'color': C['primary'], 'display': 'block', 'marginBottom': '4px'}),
                html.Span(desc, style={'color': C['txt2'], 'fontSize': '0.86rem'}),
            ], href=url, target='_blank', rel='noopener noreferrer', className='hover-card',
               style={**card({'flex': '1', 'minWidth': '260px', 'marginBottom': '0',
                              'textDecoration': 'none', 'display': 'block'})})
            for titulo, desc, url in links
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px'}),
    ], style=card())


def _agradecimentos():
    return html.Div([
        _section_title("Agradecimentos"),
        html.Div([
            ack("IFMA", "Instituto Federal do Maranhão",
                "Campus Caxias pelo suporte institucional e infraestrutura de pesquisa",
                C['primary']),
            ack("PRPGI", "Pró-Reitoria de Pesquisa, Pós-Graduação e Inovação",
                "Pelo apoio ao desenvolvimento da pesquisa científica no IFMA",
                C['secondary']),
            ack("SUS", "Sistema Único de Saúde",
                "Pelo suporte na disponibilização dos dados públicos de saúde (CNES/DATASUS)",
                C['accent']),
            ack("Orientação", "Prof. Dr. Luis Fernando Maia Santos Silva",
                "Pela orientação, dedicação e suporte ao longo de toda a pesquisa",
                C['lighter']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px'}),
    ], style=card())


def _referencias():
    return html.Div([
        _section_title("Referências"),
        html.Div([
            ref_item("AURENHAMMER, Franz; KLEIN, Rolf; LEE, Der-Tsai. ",
                     "Voronoi Diagrams and Delaunay Triangulations.",
                     " Singapore: World Scientific, 2013."),
            ref_item("BRASIL. Ministério da Saúde. ",
                     "Cadastro Nacional de Estabelecimentos de Saúde (CNES).",
                     " Disponível em: <http://cnes.datasus.gov.br>. Acesso em: 5 jul. 2026."),
            ref_item("DABIRE, Inoussa et al. ",
                     "Health Centers Network Analysis with Gephi and ForceAtlas2.",
                     " 2025."),
            ref_item("JENSEN, Tommy R.; TOFT, Bjarne. ",
                     "Graph Coloring Problems.",
                     " New York: Wiley-Interscience, 1995."),
            ref_item("LEWIS, Rhyd. ",
                     "Graph Colouring: A Visual Tour.",
                     " arXiv, 2026. Disponível em: <https://arxiv.org/>. Acesso em: 5 jul. 2026."),
            ref_item("MARX, Daniel. Graph Coloring Problems and Their Applications in Scheduling. ",
                     "Periodica Polytechnica Electrical Engineering,",
                     " v. 48, n. 1-2, p. 11-16, 2004."),
            ref_item("NETWORKX DEVELOPERS. ",
                     "NetworkX: Network Analysis in Python.",
                     " Disponível em: <https://networkx.org>. Acesso em: 5 jul. 2026."),
            ref_item("OKABE, Atsuyuki et al. ",
                     "Spatial Tessellations: Concepts and Applications of Voronoi Diagrams.",
                     " 2. ed. Chichester: John Wiley & Sons, 2000."),
        ], style={'color': C['txt2']}),
    ], style=card())


def layout():
    return html.Div([
        _hero(),
        html.Div([
            _kpis(),
            _sobre_objetivos(),
            _metodologia(),
            _glossario(),
            _links_uteis(),
            _agradecimentos(),
            _referencias(),
        ], style={'padding': '28px 40px', 'maxWidth': '1400px', 'margin': '0 auto',
                   'display': 'flex', 'flexDirection': 'column', 'gap': '4px'}),
    ])
