"""Aba 1 — Visão Geral.

Introdução, pergunta central da pesquisa, objetivos, metodologia, KPIs
principais, glossário de termos técnicos e referências.
"""
from dash import html

from colors import C, DEFAULT_RADIUS_KM, RADII_KM
from components import ack, card, kpi, ref_item, stat
from data_utils import df_all, df_geo
from graph_utils import metricas_raio

n_units = len(df_all)
n_geo = len(df_geo)
n_bairros = df_all['Bairro'].nunique()
n_cats = df_all['Categoria'].nunique()
m_default = metricas_raio(DEFAULT_RADIUS_KM)


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
            "Distribuição Espacial dos Serviços Públicos de Saúde de Caxias-MA via Teoria dos Grafos",
            style={'fontSize': '1.15rem', 'fontWeight': '400', 'color': C['lighter'], 'margin': '0 0 16px'},
        ),
        html.P(
            "Como a distribuição espacial dos serviços públicos de saúde de Caxias-MA pode ser analisada "
            "por meio da teoria dos grafos para evidenciar concentrações e possíveis vazios assistenciais? "
            "Esta plataforma modela cada estabelecimento como vértice de um grafo espacial e conecta pares "
            "dentro de um raio de proximidade geodésica, permitindo observar conectividade, isolamento e "
            "concentração — sem reduzir a análise a um único indicador.",
            style={'color': '#b7e4c7', 'maxWidth': '760px', 'lineHeight': '1.7', 'marginBottom': '24px'},
        ),
        html.Div([stat(n_units, 'estabelecimentos'), stat(n_geo, 'com geolocalização'),
                  stat(n_bairros, 'bairros'), stat(n_cats, 'categorias')],
                 style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style={
        'background': ('radial-gradient(ellipse at 85% 10%, rgba(82,183,136,0.16), transparent 55%), '
                       'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)'),
        'padding': '56px 60px',
        'borderBottom': '1px solid rgba(82,183,136,0.45)',
    })


def _kpis():
    return html.Div([
        kpi(n_units, 'Estabelecimentos ativos mapeados', C['primary']),
        kpi(n_geo, f'Com coordenada válida (raio padrão {DEFAULT_RADIUS_KM:g}km)', C['secondary']),
        kpi(m_default['n_isolados'], f'Isolados a {DEFAULT_RADIUS_KM:g}km', C['warn']),
        kpi(m_default['n_componentes'], 'Componentes conexos', C['accent']),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '4px'})


def _sobre_objetivos():
    return html.Div([
        html.Div([
            _section_title("Sobre o Projeto"),
            html.P(
                "Pesquisa vinculada ao PIBITI 2025/2026 (IFMA Campus Caxias) que integra dados "
                "geoespaciais dos serviços de saúde pública de Caxias-MA a técnicas de teoria dos "
                "grafos. Cada estabelecimento vira um vértice; arestas conectam pares cuja distância "
                "geodésica (haversine) fica dentro de um raio testado. A coloração cromática do grafo "
                "é usada como uma lente adicional de leitura — não como veredito isolado sobre "
                "qualidade da distribuição.",
                style={'lineHeight': '1.7', 'color': C['txt2']},
            ),
            html.P(
                "O dataset foi coletado por verificação in loco via Google Maps. Um estabelecimento "
                "— a Policlínica de Caxias (CNES 2453908) — teve seus dados de carga horária, "
                "profissionais e serviços complementados a partir da ficha oficial do CNES/DATASUS.",
                style={'lineHeight': '1.7', 'color': C['txt2'], 'marginBottom': '0'},
            ),
        ], style={**card(), 'flex': '1', 'marginRight': '20px'}),

        html.Div([
            _section_title("Objetivos"),
            html.Ul([
                html.Li(t, style={'marginBottom': '8px'}) for t in [
                    "Mapear e limpar os dados de estabelecimentos de saúde de Caxias-MA",
                    "Modelar a distribuição espacial como grafo de proximidade geodésica",
                    f"Testar múltiplos raios de conexão ({', '.join(f'{r:g}km' for r in RADII_KM)}) "
                    "e comparar suas métricas de conectividade",
                    "Aplicar coloração de grafos (greedy/DSATUR) como leitura complementar, nunca isolada",
                    "Apontar, com linguagem cautelosa, possíveis vazios assistenciais",
                ]
            ], style={'lineHeight': '1.8', 'color': C['txt2'], 'paddingLeft': '20px', 'margin': '0'}),
        ], style={**card(), 'flex': '1'}),
    ], style={'display': 'flex', 'flexWrap': 'wrap'})


def _metodologia():
    return html.Div([
        _section_title("Metodologia"),
        html.Ol([
            html.Li([
                html.Strong("Coleta e limpeza. "),
                "Levantamento geoespacial via verificação em campo. Registros anulados/desativados "
                "foram excluídos; estabelecimentos sem coordenada válida ficam fora do grafo mas "
                "permanecem listados.",
            ], style={'marginBottom': '10px', 'lineHeight': '1.7'}),
            html.Li([
                html.Strong("Construção do grafo espacial. "),
                "Vértices = estabelecimentos com coordenada válida; arestas = distância haversine "
                "≤ raio testado. Grafo não-direcionado, sem pesos artificiais.",
            ], style={'marginBottom': '10px', 'lineHeight': '1.7'}),
            html.Li([
                html.Strong("Métricas por raio. "),
                "Para cada raio (0,5 / 1 / 2 / 3 / 5 km): nº de vértices e arestas, grau médio, "
                "vértices isolados, componentes conexos e coloração (greedy e DSATUR aproximado).",
            ], style={'marginBottom': '10px', 'lineHeight': '1.7'}),
            html.Li([
                html.Strong("Interpretação cautelosa. "),
                "A coloração por si só não indica se a distribuição é boa ou ruim — ela é cruzada "
                "com isolamento, fragmentação em componentes e concentração geográfica antes de "
                "qualquer leitura sobre \"vazio assistencial\".",
            ], style={'marginBottom': '0', 'lineHeight': '1.7'}),
        ], style={'color': C['txt2'], 'paddingLeft': '20px'}),
    ], style=card())


def _glossario():
    termos = [
        ("Vértice / Aresta",
         "Cada estabelecimento de saúde é um vértice do grafo. Existe uma aresta entre dois "
         "vértices quando a distância geodésica entre eles é menor ou igual ao raio testado."),
        ("Distância de Haversine",
         "Fórmula que calcula a distância em linha reta entre dois pontos na superfície da Terra "
         "a partir de suas coordenadas de latitude/longitude."),
        ("Grau de um vértice",
         "Número de arestas conectadas a um vértice — quantos outros estabelecimentos estão "
         "dentro do raio de proximidade considerado."),
        ("Vértice isolado",
         "Estabelecimento sem nenhum vizinho dentro do raio testado. É um candidato a "
         "\"possível vazio assistencial\", não uma conclusão definitiva — depende do raio e do "
         "contexto (ex.: UBS rural isolada pode ser normal para a região)."),
        ("Componente conexo",
         "Subconjunto de vértices que estão todos ligados entre si por algum caminho de arestas. "
         "Um grafo com muitos componentes pequenos indica uma rede fragmentada nesse raio."),
        ("Número cromático (χ) / Coloração",
         "Menor quantidade de cores (greedy ou DSATUR aproximado) necessária para que nenhum par "
         "de vértices adjacentes compartilhe cor. Aumenta com a densidade de conexões — não deve "
         "ser lido isoladamente como indicador de qualidade da rede."),
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
            ref_item("BRASIL. Ministério da Saúde. ",
                     "Cadastro Nacional de Estabelecimentos de Saúde (CNES).",
                     " Disponível em: <http://cnes.datasus.gov.br>. Acesso em: 5 jul. 2026."),
            ref_item("JENSEN, Tommy R.; TOFT, Bjarne. ",
                     "Graph Coloring Problems.",
                     " New York: Wiley-Interscience, 1995."),
            ref_item("LEWIS, R. ",
                     "A Guide to Graph Colouring: Algorithms and Applications.",
                     " 2. ed. Cham: Springer, 2021."),
            ref_item("NETWORKX DEVELOPMENT TEAM. ",
                     "NetworkX – a Python package for the creation, manipulation, and study of "
                     "the structure, dynamics, and functions of complex networks.",
                     " Version [atual]. Disponível em: <https://networkx.org>. Acesso em: 13 mar. 2026."),
            ref_item("PANDAS DEVELOPMENT TEAM. ",
                     "pandas: powerful data analysis tools for Python.",
                     " Version [atual]. Disponível em: <https://pandas.pydata.org>. "
                     "Acesso em: 13 mar. 2026."),
            ref_item("FOLIUM DEVELOPMENT TEAM. ",
                     "folium: Python data, leaflet.js maps.",
                     " Version [atual]. Disponível em: <https://python-visualization.github.io/folium>. "
                     "Acesso em: 13 mar. 2026."),
            ref_item("DANTAS, M. N. P.; SOUZA, D. L. B. de; SOUZA, A. M. G. de; AIQUOC, K. M.; "
                     "SOUZA, T. A. de; BARBOSA, I. R. ",
                     "Fatores associados ao acesso precário aos serviços de saúde no Brasil.",
                     " Revista Brasileira de Epidemiologia, v. 24, 2021."),
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
            _agradecimentos(),
            _referencias(),
        ], style={'padding': '28px 40px', 'maxWidth': '1400px', 'margin': '0 auto',
                   'display': 'flex', 'flexDirection': 'column', 'gap': '4px'}),
    ])
