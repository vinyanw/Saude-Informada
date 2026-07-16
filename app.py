import dash
from dash import dcc, html, Input, Output, State, ctx, ALL, dash_table
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import numpy as np
import folium
from folium import plugins
import re
import json
import urllib.request
from pathlib import Path
from haversine import haversine
from scipy.spatial import Voronoi, cKDTree

# ──────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────────────────
CSV_PATH = Path("Coleta Geolocalizacional de Dados Saúde Informada .csv")
THRESHOLD_KM = 1.0

C = {
    'bg':           '#f0fdf4',
    'hdr_bg':       '#1b4332',
    'hdr_txt':      '#d8f3dc',
    'primary':      '#2d6a4f',
    'secondary':    '#40916c',
    'accent':       '#52b788',
    'light':        '#b7e4c7',
    'lighter':      '#d8f3dc',
    'white':        '#ffffff',
    'txt':          '#1b4332',
    'txt2':         '#495057',
    'border':       '#95d5b2',
    'line':         '#e3efe8',
    'warn':         '#e9c46a',
    'danger':       '#e76f51',
}

CAT_COLORS = {
    "UBS":                         "#2d6a4f",
    "UPA":                         "#e76f51",
    "SAMU":                        "#e9c46a",
    "Hospital":                    "#c1121f",
    "Maternidade":                 "#f4acb7",
    "CAPS":                        "#9b5de5",
    "CAPS / Acolhimento":          "#c77dff",
    "Centro Especializado":        "#4361ee",
    "Ambulatório / Especializado": "#4cc9f0",
    "Policlínica / Ambulatório":   "#74c69d",
    "Diagnóstico":                 "#adb5bd",
    "Ambulatório":                 "#95d5b2",
    "Clínica Especializada":       "#b7e4c7",
}

TIPO_SERVICO = {
    "UBS":                         "Não-Emergencial",
    "UPA":                         "Emergencial",
    "SAMU":                        "Emergencial",
    "Hospital":                    "Emergencial",
    "Maternidade":                 "Emergencial",
    "CAPS":                        "Não-Emergencial",
    "CAPS / Acolhimento":          "Não-Emergencial",
    "Centro Especializado":        "Não-Emergencial",
    "Ambulatório / Especializado": "Não-Emergencial",
    "Policlínica / Ambulatório":   "Não-Emergencial",
    "Diagnóstico":                 "Não-Emergencial",
    "Ambulatório":                 "Não-Emergencial",
    "Clínica Especializada":       "Não-Emergencial",
}

FOLIUM_CAT_COLORS = {
    "UBS": "blue", "UPA": "red", "SAMU": "orange",
    "Hospital": "darkred", "Maternidade": "pink",
    "CAPS": "purple", "CAPS / Acolhimento": "purple",
    "Centro Especializado": "green",
    "Ambulatório / Especializado": "cadetblue",
    "Policlínica / Ambulatório": "lightblue",
    "Diagnóstico": "gray", "Ambulatório": "lightgreen",
    "Clínica Especializada": "beige",
}

POPULATION = {
    'Centro': 18000, 'Cohab': 12000, 'Cohab II': 8000,
    'Nova Caxias': 9000, 'Castelo Branco': 7500, 'Pampulha': 7000,
    'Vila Paraiso': 5500, 'Sao Francisco': 6000, 'Vila Alecrim': 5000,
    'Santa Rita': 5500, 'Antenor Viana': 4500, 'Baixinha': 4000,
    'Salobro': 4000, 'Vila Sao Jose': 5000, 'Piraja': 4500,
    'Piquezeiro': 3500, 'Cangalheiro': 4000, 'Campo de Belem': 3500,
    'Campo de Belem II': 3000, 'Caldeiroes': 3500, 'Ponte': 3000,
    'Fazendinha': 3000, 'Mutirao': 4500, 'Trezidela': 3500,
    'Vila Arias': 4000, 'Luiza Queiroz': 3500, 'Itapecuruzinho': 3000,
    'Eugenio Coutinho': 3500, 'Bom Jesus': 3500, 'Buenos Aires': 2500,
    'Volta Redonda': 3500, 'Buriti Corrente': 1800, 'Chapada': 1500,
    'Breinho': 2000, 'Rodagem': 1500, 'Nazare do Bruno': 1800,
    'Caxirimbu': 1200, 'Povoado Santo Antonio': 1500,
    'Povoado Caxirimbu': 1000, 'Bau': 800,
}

# ──────────────────────────────────────────────────────────
# INTEGRAÇÃO IBGE — POPULAÇÃO OFICIAL (Censo 2022 + estimativas)
# ──────────────────────────────────────────────────────────
IBGE_MUN_CODE = '2103000'   # Caxias-MA
IBGE_CACHE = Path('ibge_cache.json')
POP_CENSO_2022_FALLBACK = 156973   # Censo Demográfico 2022 (agregado 4709)

IBGE_URLS = {
    'censo_2022': ('https://servicodados.ibge.gov.br/api/v3/agregados/4709/'
                   f'periodos/2022/variaveis/93?localidades=N6%5B{IBGE_MUN_CODE}%5D'),
    'estimativa': ('https://servicodados.ibge.gov.br/api/v3/agregados/6579/'
                   f'periodos/-1/variaveis/9324?localidades=N6%5B{IBGE_MUN_CODE}%5D'),
}

def fetch_ibge_population():
    """Busca a população oficial de Caxias-MA na API de agregados do IBGE
    (Censo 2022 e estimativa populacional mais recente). Grava cache local
    para funcionamento offline; em último caso usa o valor do Censo 2022."""
    import gzip
    info = {}
    try:
        for key, url in IBGE_URLS.items():
            req = urllib.request.Request(url, headers={'User-Agent': 'saude-informada/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
            if raw[:2] == b'\x1f\x8b':   # resposta comprimida (gzip)
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode())
            serie = data[0]['resultados'][0]['series'][0]['serie']
            ano, valor = sorted(serie.items())[-1]
            info[key] = int(valor)
            if key == 'estimativa':
                info['ano_estimativa'] = ano
        info['fonte'] = 'API IBGE (online)'
        IBGE_CACHE.write_text(json.dumps(info, ensure_ascii=False))
    except Exception:
        if IBGE_CACHE.exists():
            info = json.loads(IBGE_CACHE.read_text())
            info['fonte'] = 'API IBGE (cache local)'
        else:
            info = {'censo_2022': POP_CENSO_2022_FALLBACK,
                    'estimativa': POP_CENSO_2022_FALLBACK,
                    'ano_estimativa': '2022', 'fonte': 'Censo 2022 (offline)'}
    return info

IBGE = fetch_ibge_population()
POP_OFICIAL = IBGE.get('estimativa', POP_CENSO_2022_FALLBACK)

# Calibra as estimativas manuais por bairro para que a soma corresponda
# à população oficial do município (a malha por bairro não é publicada
# via API; o rateio preserva as proporções da coleta primária).
_scale = POP_OFICIAL / sum(POPULATION.values())
POPULATION = {b: int(round(p * _scale)) for b, p in POPULATION.items()}

# ──────────────────────────────────────────────────────────
# DEMANDA ASSISTENCIAL (SIA/DATASUS)
# ──────────────────────────────────────────────────────────
# Se existir um arquivo 'demanda_sia.csv' (export do TabNet/SIA com colunas
# Bairro, Atendimentos_Mes, Taxa_Ocupacao, Fila_Espera), ele é usado como
# fonte real. Na ausência, a demanda é estimada por parâmetros assistenciais
# do Ministério da Saúde (Portaria 1.631/2015: ~2,8 consultas/hab/ano).
DEMANDA_CSV = Path('demanda_sia.csv')
CONSULTAS_HAB_ANO = 2.8
CAPACIDADE_UNIDADE_MES = 704   # 4 atend/h × 8h × 22 dias úteis

def build_demanda(pop_dict, unidades_por_bairro):
    if DEMANDA_CSV.exists():
        d = pd.read_csv(DEMANDA_CSV)
        d = d.set_index('Bairro')
        return {
            b: dict(atend=int(r['Atendimentos_Mes']),
                    ocup=float(r['Taxa_Ocupacao']),
                    fila=int(r['Fila_Espera']))
            for b, r in d.iterrows()
        }, 'SIA/DATASUS (demanda_sia.csv)'
    demanda = {}
    for bairro, pop in pop_dict.items():
        atend = pop * CONSULTAS_HAB_ANO / 12
        cap = max(1, unidades_por_bairro.get(bairro, 0)) * CAPACIDADE_UNIDADE_MES
        ocup = atend / cap * 100
        fila = max(0, atend - cap)
        demanda[bairro] = dict(atend=int(round(atend)),
                               ocup=round(ocup, 1),
                               fila=int(round(fila)))
    return demanda, 'Estimativa (parâmetros assistenciais MS)'

# ──────────────────────────────────────────────────────────
# ESTUDO DE CASO — AMBULATÓRIO ESPECIALIZADO DE CAXIAS (CNES 2453908)
# Fonte: Ficha de Estabelecimento CNES/DATASUS, emitida em 28/11/2025
# ──────────────────────────────────────────────────────────
POLI_NOME = 'AMBULATORIO ESPECIALIZADO DE CAXIAS'
POLI_CNES = '2453908'

POLI_INFO = {
    'endereco': 'Rua Quininha Pires, 105 - Centro, Caxias-MA · CEP 65602-720 · Tel. (99) 98521-3410',
    'tipo': 'Policlínica · Administração Pública (Prefeitura Municipal de Caxias) · Gestão Municipal · Unidade Auxiliar de Ensino',
    'servicos': ['Oftalmologia (diagnóstico, trat. clínico e cirúrgico)',
                 'Endocrinologia e Metabologia',
                 'Traumatologia e Ortopedia',
                 'Atenção ao Paciente com Tuberculose',
                 'Atenção Integral em Hanseníase (Tipo I)',
                 'Métodos Gráficos Dinâmicos (ECG, Holter, Ergométrico)'],
    'nivel': 'Média Complexidade · Atendimento Ambulatorial e SADT · Convênio SUS · Demanda espontânea e referenciada',
    'horario': 'Atendimento contínuo 24 horas/dia (plantão: inclui sábados, domingos e feriados)',
}

POLI_EQUIPAMENTOS = [
    ('Monitor de ECG', 1), ('Eletrocardiógrafo', 1),
    ('Endoscópio Digestivo', 1), ('Tonômetro de Aplanação', 1),
]

POLI_INSTALACOES = [
    ('Clínicas Especializadas (consultórios)', 11), ('Sala de Pequena Cirurgia', 1),
    ('Sala de Curativo', 1), ('Sala de Enfermagem', 1),
    ('Sala de Gesso', 1), ('Sala de Imunização', 1),
]

_CT, _EST, _COOP = 'Contrato Temporário', 'Estatutário', 'Cooperado'

# (nome, função/CBO, CH outro, CH ambulatorial, CH hospitalar, vínculo)
POLI_PROFISSIONAIS = [
    ('Alaine Ferreira da Conceição',            'Técnico de Enfermagem',                      0, 36, 0, _CT),
    ('Amanda Nascimento Sousa',                 'Recepcionista',                             40,  0, 0, _CT),
    ('André Gustavo da Silva Lima',             'Médico Gastroenterologista',                 0, 20, 0, _CT),
    ('Andrey Emanoel Ferreira dos Reis',        'Recepcionista',                             40,  0, 0, _CT),
    ('Brenda da Silva Amancio Rodrigues',       'Diretor Administrativo',                    40,  0, 0, _CT),
    ('Brendaly Maria de Alencar Farias',        'Médico Ginecologista e Obstetra',            0, 10, 0, _CT),
    ('Cecília de Jesus Borges Santos Dorta',    'Técnico de Enfermagem',                      0, 36, 0, _EST),
    ('David Sena de Freitas',                   'Médico Oftalmologista',                      0,  4, 0, _CT),
    ('Domingos Natan de Sá Sousa',              'Assistente Administrativo',                 40,  0, 0, _CT),
    ('Edivaldo Muniz de Carvalho',              'Porteiro de Edifícios',                     40,  0, 0, _CT),
    ('Edna Cardoso Pinheiro Oliveira',          'Assistente Social',                          0, 30, 0, _CT),
    ('Elda Silva Pereira',                      'Técnico de Enfermagem',                      0, 40, 0, _CT),
    ('Eliana Ethel Costa Carvalho',             'Enfermeiro',                                 0, 40, 0, _EST),
    ('Erigilson de Sá Coutinho Beleza',         'Recepcionista',                             40,  0, 0, _CT),
    ('Eryca Giselle Leite Guimarães Silva',     'Enfermeiro',                                 0, 40, 0, _CT),
    ('Evellin Lima Nunes de Sousa',             'Médico Dermatologista',                      0, 16, 0, _CT),
    ('Francisca das Chagas de Andrade',         'Técnico de Enfermagem',                      0, 40, 0, _CT),
    ('Francisco Alexandrino de Abreu Neto',     'Médico Cirurgião Geral',                     0,  4, 0, _COOP),
    ('Francisco Antônio de Moura',              'Médico Ortopedista e Traumatologista',       0, 30, 0, _CT),
    ('Francisco Tiago Andrade de Carvalho',     'Médico Psiquiatra',                          0, 10, 0, _CT),
    ('Henrique Pinto Campelo',                  'Médico Clínico',                             6,  0, 0, _CT),
    ('Islanna Kelly Carneiro da Conceição',     'Enfermeiro',                                 0, 30, 0, _CT),
    ('Jeane Silva dos Santos',                  'Assistente Social',                          0, 30, 0, _CT),
    ('Jerusa Rodrigues Bezerra',                'Médico Cardiologista',                       0, 12, 0, _CT),
    ('Joanilde Oliveira Reis',                  'Técnico de Enfermagem',                      0, 40, 0, _EST),
    ('José Magno Sousa Magalhães',              'Médico Dermatologista',                      0, 10, 0, _COOP),
    ('José Reis Bisneto',                       'Médico em Radiologia e Diag. por Imagem',    0,  6, 0, _CT),
    ('Julina Rodrigues Lindoso',                'Técnico de Enfermagem',                      0, 36, 0, _EST),
    ('Lígia Soraya Oliveira Costa',             'Assistente Social',                          0, 30, 0, _CT),
    ('Lívio Medeiros Costa',                    'Médico Cirurgião Geral',                     0, 12, 0, _CT),
    ('Mábio de Jesus dos Santos de Assunção',   'Médico Dermatologista',                      0, 30, 0, _EST),
    ('Marcleyane Barra dos Santos',             'Médico Endocrinologista e Metabologista',    0,  8, 0, _CT),
    ('Maria da Cruz Silva de Oliveira',         'Agente de Higiene e Segurança',             40,  0, 0, _CT),
    ('Maria do Socorro Sousa Carneiro Santos',  'Agente de Higiene e Segurança',             40,  0, 0, _CT),
    ('Maria do Socorro Veras',                  'Técnico de Enfermagem',                      0, 36, 0, _CT),
    ('Maria Lucilene da Silva',                 'Agente de Higiene e Segurança',             40,  0, 0, _CT),
    ('Mariana Melo Machado',                    'Psicólogo Clínico',                          0, 30, 0, _CT),
    ('Mariton César dos Santos e Silva',        'Trabalhador de Limpeza e Conservação',      40,  0, 0, _CT),
    ('Mônica Kelly Alves dos Santos',           'Assistente Administrativo',                 40,  0, 0, _CT),
    ('Muryel Lopes Carvalho',                   'Psicólogo Clínico',                          0, 30, 0, _CT),
    ('Nancy Pereira Lima',                      'Técnico de Enfermagem',                      0, 36, 0, _EST),
    ('Nathália Caroline Torres Vilhena',        'Médico Endocrinologista e Metabologista',    0,  0, 10, _COOP),
    ('Renée Maria dos Santos Lima',             'Técnico de Enfermagem',                      0, 30, 0, _EST),
    ('Rosa Maria Rocha da Costa',               'Técnico de Enfermagem',                      0, 36, 0, _EST),
    ('Rosa Moraes Cândido',                     'Agente de Higiene e Segurança',             40,  0, 0, _CT),
    ('Rosângela Gonçalves da Silva Sousa',      'Técnico de Enfermagem',                      0, 36, 0, _EST),
    ('Sebastiana Silva dos Santos',             'Recepcionista',                             40,  0, 0, _CT),
    ('Sinésio Torres Júnior',                   'Médico Oftalmologista',                      0, 16, 0, _EST),
    ('Stefane Silva Carvalho',                  'Médico Endocrinologista e Metabologista',    0, 12, 0, _COOP),
    ('Thiago Luís Rosado Soares de Araújo',     'Médico Otorrinolaringologista',              0, 20, 0, _CT),
    ('Ubiracilda Ribeiro Chaves',               'Recepcionista',                             40,  0, 0, _CT),
    ('Victor Eulálio Sousa Campelo',            'Médico Otorrinolaringologista',              0, 12, 0, _COOP),
    ('Vinícius Macedo Martins',                 'Médico Endocrinologista e Metabologista',    0, 12, 0, _CT),
    ('Yeda Alcilene de Oliveira Ferreira',      'Técnico de Enfermagem',                      0, 30, 0, _EST),
    ('Ysmara Cristina Macedo Silva',            'Enfermeiro',                                 0, 30, 0, _CT),
]

df_poli = pd.DataFrame(POLI_PROFISSIONAIS,
                       columns=['Nome', 'Funcao', 'CH_Outro', 'CH_Amb', 'CH_Hosp', 'Vinculo'])
df_poli['CH_Total'] = df_poli['CH_Outro'] + df_poli['CH_Amb'] + df_poli['CH_Hosp']
df_poli['Medico'] = df_poli['Funcao'].str.startswith('Médico')
df_poli['Especialidade'] = df_poli['Funcao'].str.replace('Médico em ', '', regex=False).str.replace('Médico ', '', regex=False)

df_med = df_poli[df_poli['Medico']].copy()
TOTAL_H_MEDICAS = int(df_med['CH_Total'].sum())
N_ESPECIALIDADES = df_med['Especialidade'].nunique()
N_EQUIPAMENTOS = sum(q for _, q in POLI_EQUIPAMENTOS)

# ──────────────────────────────────────────────────────────
# DADOS
# ──────────────────────────────────────────────────────────
def parse_coord(s):
    if pd.isna(s) or str(s).strip() in ('NULL', ''):
        return None
    m = re.search(r'-?\d+\.?\d*,\s*-?\d+\.?\d*', str(s))
    if m:
        lat, lon = map(float, m.group(0).split(','))
        if -5.5 < lat < -4.5 and -44.0 < lon < -42.5:
            return (lat, lon)
    return None

df_raw = pd.read_csv(CSV_PATH)
df_raw['coord'] = df_raw['Coordenada de Localização'].apply(parse_coord)
df = df_raw.dropna(subset=['coord']).reset_index(drop=True)
df['Tipo'] = df['Categoria'].map(TIPO_SERVICO).fillna('Não-Emergencial')

UNIDADES_POR_BAIRRO = df.groupby('Bairro').size().to_dict()
DEMANDA, DEMANDA_FONTE = build_demanda(POPULATION, UNIDADES_POR_BAIRRO)

# ──────────────────────────────────────────────────────────
# GRAFO — construção parametrizada (threshold dinâmico + pesos)
# ──────────────────────────────────────────────────────────
THRESHOLDS_KM = [1.0, 2.0, 5.0]

# Peso de conflito da aresta por par de tipos de serviço: duas unidades
# emergenciais próximas concorrem mais fortemente por recursos do que
# um par misto (complementaridade emergência × atenção primária).
def peso_aresta(t1, t2):
    if t1 == t2 == 'Emergencial':
        return 2.0
    if t1 == t2:
        return 1.0
    return 0.5

def build_graph(data, threshold=THRESHOLD_KM, com_pesos=True):
    """Grafo de proximidade esparso: pré-filtro de vizinhança com k-d tree
    (O(n log n), escala para todo o Maranhão) e verificação haversine exata."""
    Gt = nx.Graph()
    rows = list(data.itertuples())
    for r in rows:
        Gt.add_node(r.Nome, pos=r.coord, categoria=r.Categoria,
                    bairro=r.Bairro, tipo=r.Tipo)
    pts = np.array([r.coord for r in rows])
    if len(pts) >= 2:
        # raio em graus com folga (1° ≈ 111 km no equador)
        tree = cKDTree(pts)
        for i, j in tree.query_pairs(r=threshold / 111.0 * 1.6):
            dist = haversine(rows[i].coord, rows[j].coord)
            if dist <= threshold:
                w = peso_aresta(rows[i].Tipo, rows[j].Tipo) if com_pesos else 1.0
                Gt.add_edge(rows[i].Nome, rows[j].Nome, distance=dist, weight=w)
    return Gt

def colorir(Gt):
    col = nx.greedy_color(Gt, strategy='largest_first')
    return col, (max(col.values()) + 1 if col else 0)

G = build_graph(df)
coloring, chromatic_n = colorir(G)

# ──────────────────────────────────────────────────────────
# MAPA FOLIUM
# ──────────────────────────────────────────────────────────
def make_map(cat_filter='Todos', tipo_filter='Todos', busca=''):
    m = folium.Map(location=[-4.865, -43.36], zoom_start=13, tiles="CartoDB positron")
    data = df.copy()
    if cat_filter != 'Todos':
        data = data[data['Categoria'] == cat_filter]
    if tipo_filter != 'Todos':
        data = data[data['Tipo'] == tipo_filter]
    if busca:
        data = data[data['Nome'].str.contains(busca, case=False, na=False) |
                    data['Categoria'].str.contains(busca, case=False, na=False)]
    node_set = set(data['Nome'])

    feature_groups = {}
    for cat in data['Categoria'].unique():
        feature_groups[cat] = folium.FeatureGroup(name=cat, show=True)

    edge_group = folium.FeatureGroup(name='Conexões (arestas)', show=False)

    for _, r in data.iterrows():
        lat, lon = r['coord']
        cat = r['Categoria']
        tipo = r['Tipo']
        tipo_color = '#e76f51' if tipo == 'Emergencial' else '#2d6a4f'
        popup = (
            f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:200px'>"
            f"<b style='color:#1b4332'>{r['Nome']}</b><br>"
            f"<span style='color:#2d6a4f'>Bairro:</span> {r['Bairro']}<br>"
            f"<span style='color:#2d6a4f'>Categoria:</span> {cat}<br>"
            f"<span style='color:#2d6a4f'>Tipo:</span> "
            f"<b style='color:{tipo_color}'>{tipo}</b><br>"
            f"<span style='color:#2d6a4f'>Cor cromática:</span> {coloring.get(r['Nome'], 'N/A')}"
            f"</div>"
        )
        folium.CircleMarker(
            [lat, lon],
            radius=8,
            color='white',
            weight=1.5,
            fill=True,
            fill_color=CAT_COLORS.get(cat, '#2d6a4f'),
            fill_opacity=0.9,
            popup=folium.Popup(popup, max_width=280),
            tooltip=r['Nome'],
        ).add_to(feature_groups[cat])

    for u, v in G.edges():
        if u in node_set and v in node_set:
            lat1, lon1 = G.nodes[u]['pos']
            lat2, lon2 = G.nodes[v]['pos']
            folium.PolyLine(
                [[lat1, lon1], [lat2, lon2]],
                weight=1.5, color='#40916c', opacity=0.4
            ).add_to(edge_group)

    edge_group.add_to(m)
    for fg in feature_groups.values():
        fg.add_to(m)

    # Destaque do estudo de caso (CNES 2453908)
    poli_row = df[df['Nome'] == POLI_NOME]
    if not poli_row.empty:
        lat, lon = poli_row.iloc[0]['coord']
        star_group = folium.FeatureGroup(name='★ Estudo de Caso da Policlínica', show=True)
        folium.Marker(
            [lat, lon],
            icon=folium.Icon(color='darkgreen', icon='star', prefix='fa'),
            tooltip=f"★ {POLI_NOME} (CNES {POLI_CNES}) Estudo de Caso",
            popup=folium.Popup(
                f"<div style='font-family:Inter,Helvetica,Arial,sans-serif;min-width:220px'>"
                f"<b style='color:#1b4332'>★ {POLI_NOME}</b><br>"
                f"<span style='color:#2d6a4f'>CNES:</span> {POLI_CNES}<br>"
                f"<span style='color:#2d6a4f'>Tipo:</span> Policlínica · Média Complexidade<br>"
                f"<span style='color:#2d6a4f'>Horas médicas:</span> {TOTAL_H_MEDICAS}h/sem · "
                f"{N_ESPECIALIDADES} especialidades<br>"
                f"<i>Ver aba \"Estudo de Caso da Policlínica\"</i></div>",
                max_width=300),
        ).add_to(star_group)
        star_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    plugins.Fullscreen().add_to(m)
    return m._repr_html_()

# ──────────────────────────────────────────────────────────
# VISUALIZAÇÕES PLOTLY
# ──────────────────────────────────────────────────────────
CHROM_PALETTE = [
    '#2d6a4f','#e76f51','#e9c46a','#4361ee',
    '#9b5de5','#f4acb7','#4cc9f0','#95d5b2','#ff9f1c','#2ec4b6',
]

def _edge_traces(layout, Gr=None):
    Gr = Gr if Gr is not None else G
    ex, ey = [], []
    for u, v in Gr.edges():
        x1, y1 = layout[u]; x2, y2 = layout[v]
        ex += [x1, x2, None]; ey += [y1, y2, None]
    return go.Scatter(x=ex, y=ey, mode='lines',
                      line=dict(width=0.8, color='#b7e4c7'),
                      hoverinfo='none', name='Arestas', showlegend=False)

def fig_graph_coloring(Gr=None, col=None, thr=None, com_pesos=True):
    Gr = Gr if Gr is not None else G
    col = col if col is not None else coloring
    thr = thr if thr is not None else THRESHOLD_KM
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
        go.Scatter(x=ex, y=ey, mode='lines',
                   line=dict(width=1, color='#95d5b2'), hoverinfo='none',
                   name='Arestas', showlegend=False),
        go.Scatter(x=node_x, y=node_y, mode='markers',
                   marker=dict(size=11, color=node_col, line=dict(width=1.5, color='#1b4332')),
                   text=hover, hovertemplate='%{text}<extra></extra>', name='Unidades'),
    ])
    if POLI_NOME in Gr.nodes:
        plat, plon = Gr.nodes[POLI_NOME]['pos']
        fig.add_trace(go.Scatter(
            x=[plon], y=[plat], mode='markers+text',
            marker=dict(size=22, symbol='star', color='#e9c46a',
                        line=dict(width=2, color='#1b4332')),
            text=['★ Estudo de Caso'], textposition='top center',
            textfont=dict(size=10, color=C['primary']),
            hovertemplate=(f"<b>★ {POLI_NOME}</b><br>CNES {POLI_CNES} (Estudo de Caso)<br>"
                           f"Grau no grafo: {Gr.degree(POLI_NOME)} vizinhos ≤ {thr}km"
                           "<extra></extra>"),
            showlegend=False,
        ))
    peso_txt = ' · arestas ponderadas por tipo (emergência ×2)' if com_pesos else ''
    fig.update_layout(
        title=dict(text=f'Coloração por Proximidade Geográfica (threshold {thr}km) - nº cromático: {chi}',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', showlegend=False,
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude',  gridcolor='#e8f5e9'),
        margin=dict(l=50, r=30, t=60, b=50),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
        annotations=[dict(
            text=f"Nós: {Gr.number_of_nodes()} · Arestas: {Gr.number_of_edges()} · Cores: {chi}{peso_txt}",
            xref='paper', yref='paper', x=0, y=-0.13,
            showarrow=False, font=dict(size=11, color=C['secondary'])
        )],
    )
    return fig


def fig_forceatlas2(Gr=None):
    Gr = Gr if Gr is not None else G
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
            hovertemplate='%{text}<extra></extra>',
            name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text='Rede de Serviços - Layout ForceAtlas2/Spring por Categoria',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=20, r=200, t=60, b=20),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


def fig_voronoi():
    cx, cy = -43.36, -4.865
    mask = (abs(df['coord'].apply(lambda p: p[1]) - cx) < 0.12) & \
           (abs(df['coord'].apply(lambda p: p[0]) - cy) < 0.12)
    sub = df[mask].reset_index(drop=True)
    if len(sub) < 4:
        sub = df

    pts = np.array([[r['coord'][1], r['coord'][0]] for _, r in sub.iterrows()])
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
                    fig.add_trace(go.Scatter(
                        x=[p0[0], p1[0]], y=[p0[1], p1[1]], mode='lines',
                        line=dict(color='#74c69d', width=1.2),
                        hoverinfo='none', showlegend=False,
                    ))
    except Exception:
        pass

    seen = set()
    for i, (coord, cat, name) in enumerate(zip(pts, cats, names)):
        fig.add_trace(go.Scatter(
            x=[coord[0]], y=[coord[1]], mode='markers',
            marker=dict(size=10, color=CAT_COLORS.get(cat, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{name}</b><br>Categoria: {cat}"],
            hovertemplate='%{text}<extra></extra>',
            name=cat, legendgroup=cat, showlegend=(cat not in seen),
        ))
        seen.add(cat)

    fig.update_layout(
        title=dict(text='Diagrama de Voronoi - Regiões de Influência por Unidade (área urbana)',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9'),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9', scaleanchor='x', scaleratio=1),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', hovermode='closest',
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=50, r=200, t=60, b=50),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


def fig_scheduling(Gr=None, col=None):
    Gr = Gr if Gr is not None else G
    col = col if col is not None else coloring
    chi = max(col.values()) + 1 if col else 0
    pos = nx.spring_layout(Gr, k=1.8, iterations=100, seed=77)
    traces = [_edge_traces(pos, Gr)]
    for c in range(chi):
        nodes = [n for n, cc in col.items() if cc == c]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes],
            y=[pos[n][1] for n in nodes],
            mode='markers',
            marker=dict(size=12, color=CHROM_PALETTE[c % len(CHROM_PALETTE)],
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{n}</b><br>Grupo {c+1}<br>Categoria: {Gr.nodes[n]['categoria']}" for n in nodes],
            hovertemplate='%{text}<extra></extra>',
            name=f"Grupo {c + 1}",
        ))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(
            text=f'Coloração para Alocação de Serviços - {chi} grupos sem conflito',
            font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(x=1.01, y=1, bgcolor='white', bordercolor=C['light'], borderwidth=1,
                    font=dict(size=10)),
        margin=dict(l=20, r=160, t=60, b=20),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


# ──────────────────────────────────────────────────────────
# ANÁLISE — cobertura, acessibilidade, centralidade, facility location
# ──────────────────────────────────────────────────────────
# Centroides dos bairros (média das coordenadas das unidades de cada bairro);
# fixos no cenário base — cenários simulados alteram as unidades, não os bairros.
CENTROIDES = df.groupby('Bairro')['coord'].apply(
    lambda s: (float(np.mean([c[0] for c in s])), float(np.mean([c[1] for c in s]))))

RAIO_ACESSO_KM = 2.0   # ~30 min de caminhada

def pop_voronoi_ubs(data):
    """População de cada bairro atribuída à UBS mais próxima do centroide
    (célula de Voronoi = região do vizinho mais próximo)."""
    ubs = data[data['Categoria'] == 'UBS']
    atribuida = {nome: 0 for nome in ubs['Nome']}
    bairros_atendidos = {nome: [] for nome in ubs['Nome']}
    if ubs.empty:
        return atribuida, bairros_atendidos
    for bairro, pop in POPULATION.items():
        if bairro not in CENTROIDES.index:
            continue
        cent = CENTROIDES[bairro]
        nearest = min(ubs.itertuples(), key=lambda r: haversine(cent, r.coord))
        atribuida[nearest.Nome] += pop
        bairros_atendidos[nearest.Nome].append(bairro)
    return atribuida, bairros_atendidos

def indice_acessibilidade(data, raio=RAIO_ACESSO_KM):
    """% da população residindo em bairro cujo centroide está a ≤ raio km
    de alguma UBS (proxy de acesso em ~30 minutos a pé)."""
    ubs_coords = [r.coord for r in data[data['Categoria'] == 'UBS'].itertuples()]
    if not ubs_coords:
        return 0.0
    pop_total = pop_ok = 0
    for bairro, pop in POPULATION.items():
        if bairro not in CENTROIDES.index:
            continue
        pop_total += pop
        if min(haversine(CENTROIDES[bairro], c) for c in ubs_coords) <= raio:
            pop_ok += pop
    return pop_ok / pop_total * 100 if pop_total else 0.0

def alertas_sobrecarga(data, Gr=None):
    """UBS com população de influência acima do parâmetro da PNAB e/ou
    muitos vizinhos no grafo com demanda alta no bairro."""
    Gr = Gr if Gr is not None else build_graph(data)
    atribuida, _ = pop_voronoi_ubs(data)
    alertas = []
    for nome, pop in sorted(atribuida.items(), key=lambda kv: -kv[1]):
        nivel = 'danger' if pop > 8000 else 'warn' if pop > 4000 else None
        if not nivel:
            continue
        viz = Gr.degree(nome) if nome in Gr else 0
        bairro = data.loc[data['Nome'] == nome, 'Bairro']
        ocup = DEMANDA.get(bairro.iloc[0] if len(bairro) else '', {}).get('ocup', 0)
        alertas.append(dict(
            nivel=nivel, nome=nome, pop=pop, vizinhos=viz,
            texto=f"{pop:,} hab na área de influência · {viz} vizinhos ≤ "
                  f"{THRESHOLD_KM}km · ocupação do bairro {ocup:.0f}%".replace(',', '.')))
    return alertas

def fig_centralidade(Gr=None):
    """Hubs críticos da rede: betweenness (pontes entre regiões) e
    closeness (alcance médio), ponderadas pela distância geográfica."""
    Gr = Gr if Gr is not None else G
    bet = nx.betweenness_centrality(Gr, weight='distance')
    clo = nx.closeness_centrality(Gr, distance='distance')
    top = sorted(bet, key=bet.get, reverse=True)[:12][::-1]
    fig = go.Figure([
        go.Bar(y=top, x=[bet[n] for n in top], orientation='h',
               name='Betweenness (ponte)', marker_color=C['primary'],
               hovertemplate='<b>%{y}</b><br>Betweenness: %{x:.3f}<extra></extra>'),
        go.Bar(y=top, x=[clo[n] for n in top], orientation='h',
               name='Closeness (alcance)', marker_color=C['accent'],
               hovertemplate='<b>%{y}</b><br>Closeness: %{x:.3f}<extra></extra>'),
    ])
    fig.update_layout(
        barmode='group',
        title=dict(text='Centralidade - Hubs Críticos da Rede (top 12 por betweenness)',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(title='Centralidade (ponderada pela distância)', gridcolor='#e8f5e9'),
        yaxis=dict(tickfont=dict(size=9)),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        legend=dict(x=0.65, y=0.05, bgcolor='white',
                    bordercolor=C['light'], borderwidth=1, font=dict(size=10)),
        margin=dict(l=10, r=30, t=50, b=40),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig

def sugerir_local_ubs(data, raio=RAIO_ACESSO_KM):
    """Facility location (greedy): entre os centroides de bairro, escolhe o
    local para uma nova UBS que maximiza a população descoberta passando a
    ficar a ≤ raio km de uma UBS."""
    ubs_coords = [r.coord for r in data[data['Categoria'] == 'UBS'].itertuples()]
    descobertos = [
        (b, POPULATION.get(b, 0), CENTROIDES[b]) for b in CENTROIDES.index
        if POPULATION.get(b, 0) > 0 and (
            not ubs_coords or
            min(haversine(CENTROIDES[b], c) for c in ubs_coords) > raio)
    ]
    if not descobertos:
        return None
    melhor, ganho_max = None, 0
    for b, _, cand in descobertos:
        ganho = sum(p for _, p, cent in descobertos if haversine(cand, cent) <= raio)
        if ganho > ganho_max:
            melhor, ganho_max = (b, cand), ganho
    if melhor is None:
        return None
    bairro, coord = melhor
    return dict(bairro=bairro, coord=coord, ganho=ganho_max,
                descobertos=[b for b, _, _ in descobertos])

def metricas_cenario(data, thr=None):
    """Métricas comparáveis de um cenário (base ou simulado)."""
    thr = thr if thr is not None else THRESHOLD_KM
    Gt = build_graph(data, thr)
    col, chi = colorir(Gt)
    atribuida, _ = pop_voronoi_ubs(data)
    vals = [v for v in atribuida.values()]
    graus = [d for _, d in Gt.degree()]
    return dict(
        n=len(data), ubs=int((data['Categoria'] == 'UBS').sum()),
        arestas=Gt.number_of_edges(), chi=chi,
        grau_medio=float(np.mean(graus)) if graus else 0.0,
        acess=indice_acessibilidade(data),
        hab_ubs=float(np.mean(vals)) if vals else 0.0,
        sobrecarga=sum(1 for v in vals if v > 4000),
        alertas=alertas_sobrecarga(data, Gt),
        G=Gt, col=col,
    )

METRICAS_BASE = None   # calculado sob demanda (cache) no callback de cenários

def get_metricas_base():
    global METRICAS_BASE
    if METRICAS_BASE is None:
        METRICAS_BASE = metricas_cenario(df)
    return METRICAS_BASE


def fig_pop_voronoi():
    """Cobertura populacional robusta: população calibrada pelo IBGE atribuída
    à UBS mais próxima do centroide de cada bairro. Referência: Portaria
    2.436/2017 (~2.000–4.000 pessoas por equipe de atenção básica)."""
    atribuida, bairros_atendidos = pop_voronoi_ubs(df)
    ordem = sorted(atribuida, key=atribuida.get, reverse=True)
    vals = [atribuida[n] for n in ordem]
    cores = [C['danger'] if v > 8000 else C['warn'] if v > 4000 else C['secondary']
             for v in vals]
    hover = [f"<b>{n}</b><br>Hab. na área de influência: {atribuida[n]:,}".replace(',', '.') +
             f"<br>Bairros: {', '.join(bairros_atendidos[n]) or '-'}"
             for n in ordem]

    fig = go.Figure(go.Bar(
        x=ordem, y=vals, marker_color=cores,
        text=hover, hovertemplate='%{text}<extra></extra>',
    ))
    fig.add_hline(y=4000, line_dash='dash', line_color=C['warn'],
                  annotation_text='Limite recomendado por equipe (Portaria 2.436/2017: 4.000 hab)',
                  annotation_font=dict(size=10, color=C['txt2']))
    fig.update_layout(
        title=dict(text=f'Habitantes por UBS (Área de Influência Voronoi) '
                        f'(população {IBGE.get("ano_estimativa", "2022")} · {IBGE["fonte"]})',
                   font=dict(size=13, color=C['primary'])),
        xaxis=dict(tickangle=-45, gridcolor='#e8f5e9', tickfont=dict(size=9)),
        yaxis=dict(title='Habitantes atribuídos', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        margin=dict(l=50, r=20, t=60, b=160), showlegend=False,
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


# ──────────────────────────────────────────────────────────
# VISUALIZAÇÕES — ESTUDO DE CASO (POLICLÍNICA)
# ──────────────────────────────────────────────────────────
def fig_ch_especialidade():
    """Barras horizontais empilhadas: CH semanal por especialidade,
    um segmento por médico."""
    esp_total = df_med.groupby('Especialidade')['CH_Total'].sum().sort_values()
    ordem = esp_total.index.tolist()
    fig = go.Figure()
    for i, (_, r) in enumerate(df_med.sort_values('CH_Total', ascending=False).iterrows()):
        fig.add_trace(go.Bar(
            y=[r['Especialidade']], x=[r['CH_Total']], orientation='h',
            marker=dict(color=CHROM_PALETTE[i % len(CHROM_PALETTE)],
                        line=dict(width=1, color='white')),
            text=[f"<b>{r['Nome']}</b><br>{r['Funcao']}<br>CH amb.: {r['CH_Amb']}h · "
                  f"CH total: {r['CH_Total']}h/sem<br>Vínculo: {r['Vinculo']}"],
            hovertemplate='%{text}<extra></extra>', showlegend=False,
        ))
    for esp, total in esp_total.items():
        fig.add_annotation(y=esp, x=total, text=f" {int(total)}h",
                           showarrow=False, xanchor='left',
                           font=dict(size=11, color=C['primary']))
    fig.update_layout(
        barmode='stack',
        title=dict(text='Carga Horária Semanal por Especialidade Médica '
                        '(cada segmento = um médico)',
                   font=dict(size=13, color=C['primary'])),
        yaxis=dict(categoryorder='array', categoryarray=ordem, tickfont=dict(size=11)),
        xaxis=dict(title='Horas/semana', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        margin=dict(l=10, r=60, t=50, b=40),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


def fig_poli_ego():
    """Subgrafo de vizinhança da Policlínica no grafo de proximidade."""
    if POLI_NOME not in G.nodes:
        return go.Figure()
    ego = nx.ego_graph(G, POLI_NOME, radius=1)
    pos = nx.spring_layout(ego, k=1.5, iterations=100, seed=7)
    ex, ey = [], []
    for u, v in ego.edges():
        x1, y1 = pos[u]; x2, y2 = pos[v]
        ex += [x1, x2, None]; ey += [y1, y2, None]
    traces = [go.Scatter(x=ex, y=ey, mode='lines',
                         line=dict(width=1, color='#b7e4c7'),
                         hoverinfo='none', showlegend=False)]
    for n in ego.nodes():
        is_poli = (n == POLI_NOME)
        cat = ego.nodes[n]['categoria']
        traces.append(go.Scatter(
            x=[pos[n][0]], y=[pos[n][1]], mode='markers',
            marker=dict(
                size=26 if is_poli else 12,
                symbol='star' if is_poli else 'circle',
                color='#e9c46a' if is_poli else CAT_COLORS.get(cat, C['secondary']),
                line=dict(width=2 if is_poli else 1.5, color='#1b4332')),
            text=[f"<b>{'★ ' if is_poli else ''}{n}</b><br>Categoria: {cat}<br>"
                  f"Bairro: {ego.nodes[n]['bairro']}"],
            hovertemplate='%{text}<extra></extra>', showlegend=False,
        ))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text=f'Vizinhança no Grafo de Proximidade - '
                        f'{G.degree(POLI_NOME)} unidades a ≤ {THRESHOLD_KM}km',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig


def poli_recomendacoes():
    """Recomendações automáticas derivadas dos dados do CNES."""
    recs = []
    esp = df_med.groupby('Especialidade').agg(
        ch=('CH_Total', 'sum'), n=('Nome', 'count'))

    baixa = esp[esp['ch'] < 20].sort_values('ch')
    for e, r in baixa.iterrows():
        recs.append(('danger' if r['ch'] <= 10 else 'warn',
                     f"Baixa oferta em {e}",
                     f"Apenas {int(r['ch'])}h/semana ({int(r['n'])} médico(s)). "
                     f"Considerar ampliação de carga horária ou contratação - oferta "
                     f"inferior a 20h/sem limita o acesso via regulação."))

    unicos = esp[esp['n'] == 1]
    nomes_unicos = ', '.join(unicos.index)
    if len(unicos):
        recs.append(('warn', "Especialidades com profissional único",
                     f"{nomes_unicos}: a oferta depende de um único médico - férias ou "
                     f"desligamento interrompem o serviço. Avaliar redundância mínima."))

    ch_hosp = df_poli[df_poli['CH_Hosp'] > 0]
    for _, r in ch_hosp.iterrows():
        recs.append(('warn', "Carga horária hospitalar em unidade ambulatorial",
                     f"{r['Nome']} ({r['Funcao']}) tem {r['CH_Hosp']}h registradas como "
                     f"hospitalares em estabelecimento exclusivamente ambulatorial - "
                     f"verificar consistência do cadastro no CNES."))

    coop = df_med[df_med['Vinculo'] == _COOP]
    pct_coop = len(coop) / len(df_med) * 100
    if pct_coop > 20:
        recs.append(('warn', "Dependência de vínculos intermediados",
                     f"{len(coop)} de {len(df_med)} médicos ({pct_coop:.0f}%) atuam como "
                     f"cooperados/intermediados, vínculo de menor estabilidade para a rede."))

    temp = df_poli[df_poli['Vinculo'] == _CT]
    recs.append(('info', "Vínculos temporários predominantes",
                 f"{len(temp)} de {len(df_poli)} profissionais "
                 f"({len(temp)/len(df_poli)*100:.0f}%) têm contrato por prazo determinado. "
                 f"Alta rotatividade potencial compromete a continuidade assistencial."))

    media_esp = TOTAL_H_MEDICAS / max(1, N_ESPECIALIDADES)
    recs.append(('info', "Funcionamento 24h vs. oferta médica concentrada",
                 f"A unidade registra atendimento contínuo 24h/dia (168h/sem), mas a oferta "
                 f"média é de apenas {media_esp:.0f}h semanais por especialidade "
                 f"({TOTAL_H_MEDICAS}h ÷ {N_ESPECIALIDADES} especialidades) - divulgar a "
                 f"grade de horários por especialidade evita demanda frustrada fora da escala."))
    return recs


# ──────────────────────────────────────────────────────────
# HELPERS DE ESTILO
# ──────────────────────────────────────────────────────────
def card(extra=None):
    s = {'background': C['white'], 'border': f"1px solid {C['line']}",
         'borderRadius': '14px',
         'boxShadow': '0 1px 2px rgba(27,67,50,0.05), 0 8px 24px rgba(27,67,50,0.06)',
         'padding': '26px 28px', 'marginBottom': '20px'}
    if extra:
        s.update(extra)
    return s

def _kpi(value, label, color):
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

TAB_S = {
    'padding': '14px 26px', 'fontWeight': '600', 'fontSize': '13.5px',
    'backgroundColor': 'transparent', 'color': C['txt2'],
    'border': 'none', 'borderBottom': '3px solid transparent',
    'letterSpacing': '0.01em',
}
TAB_SEL = {**TAB_S, 'color': C['primary'],
           'borderBottom': f"3px solid {C['accent']}",
           'backgroundColor': 'rgba(82,183,136,0.07)'}

HDR = {
    'background': 'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)',
    'color': C['hdr_txt'],
    'padding': '18px 40px', 'borderBottom': '1px solid rgba(82,183,136,0.45)',
    'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between',
}

# ──────────────────────────────────────────────────────────
# LAYOUT: LANDING
# ──────────────────────────────────────────────────────────
n_units  = len(df)
n_bairros = df['Bairro'].nunique()
n_cats   = df['Categoria'].nunique()

def _stat(value, label):
    return html.Div([
        html.Span(str(value), style={'fontSize': '2.2rem', 'fontWeight': '600', 'color': '#74c69d',
                                     'fontFamily': '"JetBrains Mono", monospace',
                                     'letterSpacing': '-0.02em'}),
        html.Span(f" {label}", style={'color': C['lighter'], 'marginRight': '32px',
                                      'fontSize': '0.9rem', 'letterSpacing': '0.03em'}),
    ])

def _step(n, title, text):
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

def _ack(label, title, sub, border_color):
    return html.Div([
        html.Div(label, style={
            'fontWeight': '700', 'fontSize': '1.3rem', 'color': C['primary'],
            'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '10px', 'marginBottom': '8px',
        }),
        html.P(title, style={'fontWeight': '600', 'color': C['primary'], 'marginBottom': '4px'}),
        html.P(sub, style={'fontSize': '0.88rem', 'color': C['txt2'], 'margin': '0'}),
    ], className='hover-card',
       style={**card({'borderTop': f'3px solid {border_color}', 'flex': '1', 'marginBottom': '0'})})

def _ref(authors, title, rest):
    return html.P([authors, html.Strong(title), rest],
                  style={'marginBottom': '14px', 'lineHeight': '1.7', 'fontSize': '0.9rem'})

tab_landing = html.Div([
    # Hero
    html.Div([
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
        html.Div([_stat(n_units, 'unidades'), _stat(n_bairros, 'bairros'),
                  _stat(n_cats, 'categorias'), _stat(chromatic_n, 'cores')],
                 style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style={
        'background': ('radial-gradient(ellipse at 85% 10%, rgba(82,183,136,0.16), transparent 55%), '
                       'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)'),
        'padding': '56px 60px',
        'borderBottom': '1px solid rgba(82,183,136,0.45)',
    }),

    # Content
    html.Div([
        # Sobre + Objetivos
        html.Div([
            html.Div([
                html.H3("Sobre o Projeto", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
                }),
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
                html.H3("Objetivos", style={
                    'color': C['primary'], 'marginTop': '0',
                    'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
                }),
                html.Ul([
                    html.Li(t, style={'marginBottom': '8px'}) for t in [
                        "Mapear e catalogar serviços de saúde de Caxias-MA com coordenadas geográficas validadas",
                        "Modelar a distribuição como grafo de proximidade (threshold 2 km)",
                        "Aplicar algoritmos de coloração para análise de conflitos e cobertura",
                        "Identificar gaps e redundâncias na rede de atenção à saúde",
                        "Comparar abordagens distintas de abstração e visualização de redes de saúde",
                        "Disponibilizar visualizações interativas para apoio à gestão em saúde pública",
                    ]
                ], style={'lineHeight': '1.8', 'color': C['txt2'], 'paddingLeft': '20px', 'margin': '0'}),
            ], style={**card(), 'flex': '1'}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),

        # Metodologia
        html.Div([
            html.H3("Metodologia", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
            }),
            html.Div([
                _step(1, "Coleta de Dados",
                      "Levantamento geoespacial via CNES/DATASUS e Google Maps. "
                      "Validação manual de coordenadas e categorização por tipo de serviço."),
                _step(2, "Construção do Grafo",
                      "Vértices = unidades de saúde; arestas = proximidade ≤ 2km (haversine). "
                      "Grafo não-direcionado implementado com NetworkX."),
                _step(3, "Coloração Cromática",
                      f"Algoritmo greedy (largest_first) determinou número cromático χ = {chromatic_n}. "
                      "Cada cor representa um grupo de serviços sem conflito de adjacência."),
                html.Div([
                    html.Div("4", style={
                        'width': '34px', 'height': '34px', 'borderRadius': '10px',
            'background': f"linear-gradient(135deg, {C['primary']}, {C['accent']})",
            'boxShadow': '0 4px 10px rgba(45,106,79,0.25)',
                        'color': 'white', 'display': 'flex', 'alignItems': 'center',
                        'justifyContent': 'center', 'fontWeight': '700', 'marginBottom': '10px',
                    }),
                    html.H4("Análise e Visualização", style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '8px'}),
                    html.P(
                        "Diagramas de Voronoi, grafos com force-layout e mapa interativo revelam "
                        "cobertura por bairro, gaps e padrões topológicos da rede.",
                        style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6', 'margin': '0'},
                    ),
                ], style={'flex': '1', 'padding': '16px', 'minWidth': '200px'}),
            ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        ], style=card()),

        # Agradecimentos
        html.Div([
            html.H3("Agradecimentos", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
            }),
            html.Div([
                _ack("IFMA", "Instituto Federal do Maranhão",
                     "Campus Caxias pelo suporte institucional e infraestrutura de pesquisa",
                     C['primary']),
                _ack("PRPGI", "Pró-Reitoria de Pesquisa, Pós-Graduação e Inovação",
                     "Pelo apoio ao desenvolvimento da pesquisa científica no IFMA",
                     C['secondary']),
                _ack("SUS", "Sistema Único de Saúde",
                     "Pelo suporte na disponibilização dos dados públicos de saúde (CNES/DATASUS)",
                     C['accent']),
                _ack("Orientação", "Prof. Dr. Luis Fernando Maia Santos Silva",
                     "Pela orientação, dedicação e suporte ao longo de toda a pesquisa",
                     C['lighter']),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px'}),
        ], style=card()),

        # Referências ABNT
        html.Div([
            html.H3("Referências", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
            }),
            html.Div([
                _ref("AURENHAMMER, Franz; KLEIN, Rolf; LEE, Der-Tsai. ",
                     "Voronoi Diagrams and Delaunay Triangulations.",
                     " Singapore: World Scientific, 2013."),
                _ref("BRASIL. Ministério da Saúde. ",
                     "Cadastro Nacional de Estabelecimentos de Saúde (CNES).",
                     " Disponível em: <http://cnes.datasus.gov.br>. Acesso em: 5 jul. 2026."),
                _ref("DABIRE, Inoussa et al. ",
                     "Health Centers Network Analysis with Gephi and ForceAtlas2.",
                     " 2025."),
                _ref("JENSEN, Tommy R.; TOFT, Bjarne. ",
                     "Graph Coloring Problems.",
                     " New York: Wiley-Interscience, 1995."),
                _ref("LEWIS, Rhyd. ",
                     "Graph Colouring: A Visual Tour.",
                     " arXiv, 2026. Disponível em: <https://arxiv.org/>. Acesso em: 5 jul. 2026."),
                _ref("MARX, Daniel. Graph Coloring Problems and Their Applications in Scheduling. ",
                     "Periodica Polytechnica Electrical Engineering,",
                     " v. 48, n. 1-2, p. 11-16, 2004."),
                _ref("NETWORKX DEVELOPERS. ",
                     "NetworkX: Network Analysis in Python.",
                     " Disponível em: <https://networkx.org>. Acesso em: 5 jul. 2026."),
                _ref("OKABE, Atsuyuki et al. ",
                     "Spatial Tessellations: Concepts and Applications of Voronoi Diagrams.",
                     " 2. ed. Chichester: John Wiley & Sons, 2000."),
            ], style={'color': C['txt2']}),
        ], style=card()),

    ], style={'padding': '28px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
])


# ──────────────────────────────────────────────────────────
# LAYOUT: MAPA E COBERTURA
# ──────────────────────────────────────────────────────────
all_cats = ['Todos'] + sorted(df['Categoria'].unique().tolist())

_KPI_BASE = get_metricas_base()

tab_mapa = html.Div([
    # Dashboard de KPIs operacionais
    html.Div([
        _kpi(f"{_KPI_BASE['acess']:.1f}%",
             f"da população a ≤ {RAIO_ACESSO_KM:g}km de uma UBS (acessibilidade)",
             C['primary']),
        _kpi(f"{_KPI_BASE['hab_ubs']:,.0f}".replace(',', '.'),
             "habitantes por UBS (média - área de influência Voronoi)",
             C['secondary']),
        _kpi(_KPI_BASE['sobrecarga'],
             "UBS sobrecarregadas (> 4.000 hab na área de influência)",
             C['danger'] if _KPI_BASE['sobrecarga'] else C['accent']),
        _kpi(_KPI_BASE['chi'],
             f"grupos p/ escalonamento sem conflito (χ, raio {THRESHOLD_KM:g}km)",
             C['warn']),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

    html.Div([
        # Sidebar
        html.Div([
            html.H3("Filtros", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em', 'marginBottom': '16px',
            }),
            html.Label("Buscar unidade", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
            dcc.Input(
                id='filter-busca', type='text', debounce=True,
                placeholder='ex.: UBS, CAPS, oftalmo…',
                style={'width': '100%', 'padding': '7px 10px', 'marginTop': '8px',
                       'marginBottom': '16px', 'border': f"1px solid {C['line']}",
                       'fontSize': '0.86rem', 'boxSizing': 'border-box'},
            ),
            html.Label("Categoria de Serviço", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
            dcc.Dropdown(
                id='filter-cat',
                options=[{'label': c, 'value': c} for c in all_cats],
                value='Todos', clearable=False,
                style={'marginTop': '8px', 'marginBottom': '16px'},
            ),
            html.Label("Tipo de Atendimento", style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
            dcc.Dropdown(
                id='filter-tipo',
                options=[
                    {'label': 'Todos', 'value': 'Todos'},
                    {'label': 'Emergencial', 'value': 'Emergencial'},
                    {'label': 'Não-Emergencial', 'value': 'Não-Emergencial'},
                ],
                value='Todos', clearable=False,
                style={'marginTop': '8px', 'marginBottom': '20px'},
            ),
            html.H4("Resumo", style={
                'color': C['primary'], 'borderBottom': f"1px solid {C['light']}",
                'paddingBottom': '8px', 'marginTop': '0',
            }),
            html.Div(id='map-summary'),
            html.H4("Legenda", style={
                'color': C['primary'], 'marginTop': '20px',
                'borderBottom': f"1px solid {C['light']}", 'paddingBottom': '8px',
            }),
            html.Div([
                html.Div([
                    html.Div(style={
                        'width': '13px', 'height': '13px',
                        'backgroundColor': col, 'marginRight': '8px', 'flexShrink': '0',
                    }),
                    html.Span(cat, style={'fontSize': '0.8rem', 'color': C['txt2']}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'})
                for cat, col in CAT_COLORS.items()
            ]),
        ], style={
            'width': '250px', 'flexShrink': '0',
            'backgroundColor': C['white'], 'border': f"1px solid {C['line']}",
            'borderRadius': '14px 0 0 14px',
            'padding': '20px', 'overflowY': 'auto',
        }),
        # Map
        html.Div([
            html.Iframe(id='map-frame', srcDoc='',
                        style={'width': '100%', 'height': '100%', 'border': 'none'}),
        ], style={
            'flex': '1', 'height': '580px',
            'border': f"1px solid {C['line']}", 'borderLeft': 'none',
            'borderRadius': '0 14px 14px 0', 'overflow': 'hidden',
            'backgroundColor': C['white'],
        }),
    ], style={'display': 'flex', 'marginBottom': '20px', 'height': '580px',
              'boxShadow': '0 8px 24px rgba(27,67,50,0.06)',
              'borderRadius': '14px'}),

    # Charts row
    html.Div([
        html.Div([
            dcc.Graph(id='bar-chart', config={'displayModeBar': False}, style={'height': '360px'}),
        ], style={**card({'flex': '1.6', 'marginRight': '20px', 'padding': '16px', 'marginBottom': '0'})}),

        html.Div([
            html.H4("Distribuição por Categoria", style={
                'color': C['primary'], 'marginTop': '0',
                'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '10px',
            }),
            dcc.Graph(id='pie-chart', config={'displayModeBar': False}, style={'height': '300px'}),
        ], style={**card({'flex': '1', 'padding': '16px', 'marginBottom': '0'})}),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '20px'}),

    # Table
    html.Div([
        html.Div([
            html.H3("Cobertura por Bairro", style={
                'color': C['primary'], 'marginTop': '0', 'marginBottom': '0',
            }),
            html.Button("⬇ Exportar CSV", id='btn-export-cov', n_clicks=0, style={
                'padding': '8px 16px', 'backgroundColor': C['secondary'], 'color': 'white',
                'border': 'none', 'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.85rem',
            }),
            dcc.Download(id='dl-cov'),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                  'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em'}),
        html.P(
            f"População calibrada por dados oficiais do IBGE - Censo 2022: "
            f"{IBGE.get('censo_2022', POP_CENSO_2022_FALLBACK):,} hab · "
            f"Estimativa {IBGE.get('ano_estimativa', '—')}: {POP_OFICIAL:,} hab "
            f"({IBGE['fonte']}). Demanda assistencial: {DEMANDA_FONTE}.".replace(',', '.'),
            style={'fontSize': '0.82rem', 'color': C['txt2'], 'fontStyle': 'italic'},
        ),
        html.Div(id='cov-table'),
    ], style=card()),

    # Voronoi coverage
    html.Div([
        html.H3("Validação de Cobertura - População por Área de Influência (Voronoi)", style={
            'color': C['primary'], 'marginTop': '0',
            'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px', 'letterSpacing': '-0.01em',
        }),
        html.P(
            "Cada bairro é atribuído à UBS mais próxima de seu centroide (região de Voronoi). "
            "Barras acima de 4.000 habitantes indicam UBS potencialmente sobrecarregadas "
            "segundo o parâmetro da Portaria 2.436/2017 (PNAB).",
            style={'fontSize': '0.88rem', 'color': C['txt2'], 'lineHeight': '1.6'},
        ),
        dcc.Graph(figure=fig_pop_voronoi(), config={'displayModeBar': False},
                  style={'height': '460px'}),
    ], style=card()),

], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto',
          'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT: GRAFOS
# ──────────────────────────────────────────────────────────
def method_section(title, authors, year, source, description, figure=None, graph_id=None):
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

tab_grafos = html.Div([
    html.Div([
        html.H2("Visualização de Grafos", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Metodologias de abstração e visualização aplicadas à rede de serviços de Caxias-MA. "
            "Ajuste o raio de proximidade e a ponderação das arestas - os grafos são recalculados "
            "automaticamente.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        # Controles de modelagem
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
                html.Label("Pesos nas arestas",
                           style={'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.88rem'}),
                dcc.Checklist(
                    id='graf-pesos',
                    options=[{'label': ' Ponderar por tipo de serviço '
                                       '(emergência×emergência = 2,0 · mesmo tipo = 1,0 · misto = 0,5)',
                              'value': 'pesos'}],
                    value=['pesos'],
                    style={'marginTop': '8px', 'color': C['txt2'], 'fontSize': '0.86rem'},
                ),
            ], style={'flex': '2', 'minWidth': '300px'}),
            html.Div(id='graf-stats', style={'flex': '1', 'minWidth': '200px',
                                             'textAlign': 'right', 'color': C['primary'],
                                             'fontWeight': '600', 'fontSize': '0.9rem'}),
        ], style={**card({'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px',
                          'alignItems': 'center'})}),

        method_section(
            "Graph Colouring: A Visual Tour",
            "Rhyd Lewis", "2026", "arXiv",
            "Arestas conectam unidades dentro do raio selecionado (distância haversine). "
            "Coloração cromática (greedy, largest_first) destaca conflitos de proximidade, "
            "serviços do mesmo tipo muito próximos e complementaridades entre categorias distintas. "
            "Posições dos nós correspondem às coordenadas geográficas reais.",
            graph_id='g-coloring',
        ),

        method_section(
            "Health Centers Network Analysis with Gephi and ForceAtlas2",
            "Dabire et al.", "2025", "Gephi / ForceAtlas2",
            "Layout baseado em força (spring layout como aproximação do ForceAtlas2): "
            "a topologia da rede emerge da estrutura de conexões, independente da posição geográfica. "
            "Nós coloridos por categoria de serviço. A proximidade visual reflete densidade de conexões.",
            graph_id='g-force',
        ),

        method_section(
            "Centralidade em Redes - Identificação de Hubs Críticos",
            "Freeman; Brandes", "1977/2001", "Análise de Redes Sociais",
            "Betweenness identifica unidades-ponte por onde passam os menores caminhos da rede "
            "(a remoção fragmenta o sistema); closeness mede o alcance médio de cada unidade às demais. "
            "Ambas ponderadas pela distância geográfica - valores altos indicam hubs prioritários "
            "para investimento e contingência.",
            graph_id='g-central',
        ),

        method_section(
            "Voronoi Diagrams em Facility Location",
            "Aurenhammer, Klein & Lee; Okabe et al.", "2000/2013", "Geometria Computacional",
            "Tesselação de Voronoi sobre as coordenadas das unidades da área urbana central de Caxias. "
            "Cada polígono delimita a região de influência natural de uma unidade, "
            "onde ela é o serviço geograficamente mais próximo. "
            "Facilita identificação de gaps de cobertura, sobreposição e redundâncias.",
            figure=fig_voronoi(),
        ),

        method_section(
            "Graph Coloring Applied to Service Allocation and Scheduling",
            "Marx, D.", "2004", "Periodica Polytechnica Electrical Engineering",
            "Extensão da coloração ao problema de alocação de recursos: cada grupo de cor representa "
            "um conjunto de unidades que podem operar em um mesmo turno ou receber a mesma categoria "
            "de recurso sem conflito. O número de grupos necessários (χ) varia com o raio de "
            "proximidade selecionado acima.",
            graph_id='g-sched',
        ),

    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
], style={'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT: ESTUDO DE CASO — POLICLÍNICA
# ──────────────────────────────────────────────────────────
def _info_card(titulo, conteudo, border_color):
    return html.Div([
        html.H4(titulo, style={'color': C['primary'], 'marginTop': '0',
                               'borderBottom': f"1px solid {C['line']}",
                               'paddingBottom': '8px', 'marginBottom': '10px'}),
        conteudo,
    ], className='hover-card',
       style={**card({'flex': '1', 'minWidth': '260px',
                      'borderLeft': f'3px solid {border_color}', 'marginBottom': '0'})})

def _rec_card(nivel, titulo, texto):
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

def _sec_title(txt):
    return html.H3(txt, style={'color': C['primary'], 'marginTop': '0',
                               'borderBottom': f"1px solid {C['line']}",
                               'borderLeft': f"3px solid {C['accent']}",
                               'paddingLeft': '12px', 'letterSpacing': '-0.01em',
                               'paddingBottom': '10px'})

tab_policlinica = html.Div([
    html.Div([
        # Título
        html.Div([
            html.H2("Análise Detalhada: Ambulatório Especializado de Caxias (CNES 2453908)",
                    style={'color': C['primary'], 'margin': '0 0 6px'}),
            html.P(f"Estudo de caso a partir da Ficha de Estabelecimento CNES/DATASUS "
                   f"(emitida em 28/11/2025) · {len(df_poli)} profissionais cadastrados · "
                   f"unidade destacada com ★ no mapa e no grafo de proximidade.",
                   style={'color': C['txt2'], 'marginBottom': '24px'}),
        ]),

        # Indicadores chave
        html.Div([
            _kpi(f"{TOTAL_H_MEDICAS}h", "horas médicas semanais", C['primary']),
            _kpi(N_ESPECIALIDADES, "especialidades médicas", C['secondary']),
            _kpi(N_EQUIPAMENTOS, "equipamentos em uso (SUS)", C['accent']),
            _kpi(len(df_poli), "profissionais no CNES", C['warn']),
            _kpi(11, "consultórios especializados", C['danger']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        # Cards de identificação CNES
        html.Div([
            _info_card("📍 Endereço e Contato",
                       html.P(POLI_INFO['endereco'],
                              style={'color': C['txt2'], 'fontSize': '0.88rem',
                                     'lineHeight': '1.7', 'margin': '0'}),
                       C['primary']),
            _info_card("🏥 Tipo de Estabelecimento",
                       html.P(POLI_INFO['tipo'],
                              style={'color': C['txt2'], 'fontSize': '0.88rem',
                                     'lineHeight': '1.7', 'margin': '0'}),
                       C['secondary']),
            _info_card("⚕️ Nível de Atenção",
                       html.P(POLI_INFO['nivel'],
                              style={'color': C['txt2'], 'fontSize': '0.88rem',
                                     'lineHeight': '1.7', 'margin': '0'}),
                       C['accent']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '16px'}),

        html.Div([
            _info_card("🩺 Serviços Principais",
                       html.Ul([html.Li(s, style={'marginBottom': '5px'})
                                for s in POLI_INFO['servicos']],
                               style={'color': C['txt2'], 'fontSize': '0.86rem',
                                      'lineHeight': '1.6', 'paddingLeft': '18px', 'margin': '0'}),
                       C['primary']),
            _info_card("🕐 Horário de Funcionamento",
                       html.Div([
                           html.P(POLI_INFO['horario'],
                                  style={'color': C['txt2'], 'fontSize': '0.88rem',
                                         'lineHeight': '1.7', 'marginTop': '0'}),
                           html.P("Fluxo de clientela: demanda espontânea e referenciada.",
                                  style={'color': C['txt2'], 'fontSize': '0.85rem',
                                         'fontStyle': 'italic', 'margin': '0'}),
                       ]),
                       C['warn']),
            _info_card("🔬 Equipamentos e Instalações",
                       html.Div([
                           html.P(" · ".join(f"{n} ({q})" for n, q in POLI_EQUIPAMENTOS),
                                  style={'color': C['txt2'], 'fontSize': '0.86rem',
                                         'lineHeight': '1.7', 'marginTop': '0'}),
                           html.P(" · ".join(f"{n}: {q}" for n, q in POLI_INSTALACOES),
                                  style={'color': C['txt2'], 'fontSize': '0.82rem', 'margin': '0'}),
                       ]),
                       C['secondary']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        # Gráfico CH por especialidade
        html.Div([
            _sec_title("Carga Horária por Especialidade Médica"),
            dcc.Graph(figure=fig_ch_especialidade(),
                      config={'displayModeBar': False}, style={'height': '480px'}),
        ], style=card()),

        # Tabela de profissionais
        html.Div([
            _sec_title("Profissionais Cadastrados no CNES"),
            html.Div([
                html.P("Tabela interativa: ordene clicando no cabeçalho e filtre digitando "
                       "nas caixas abaixo dos títulos das colunas.",
                       style={'fontSize': '0.84rem', 'color': C['txt2'],
                              'fontStyle': 'italic', 'margin': '0'}),
                html.Button("⬇ Exportar CSV", id='btn-export-poli', n_clicks=0, style={
                    'padding': '8px 16px', 'backgroundColor': C['secondary'], 'color': 'white',
                    'border': 'none', 'fontWeight': '600', 'cursor': 'pointer',
                    'fontSize': '0.85rem', 'flexShrink': '0',
                }),
                dcc.Download(id='dl-poli'),
            ], style={'display': 'flex', 'justifyContent': 'space-between',
                      'alignItems': 'center', 'gap': '12px', 'marginBottom': '10px'}),
            dash_table.DataTable(
                data=df_poli[['Nome', 'Funcao', 'CH_Amb', 'CH_Total', 'Vinculo']]
                    .rename(columns={'Funcao': 'Especialidade / Função',
                                     'CH_Amb': 'CH Ambulatorial (h/sem)',
                                     'CH_Total': 'CH Total (h/sem)',
                                     'Vinculo': 'Vínculo'}).to_dict('records'),
                columns=[{'name': c, 'id': c} for c in
                         ['Nome', 'Especialidade / Função', 'CH Ambulatorial (h/sem)',
                          'CH Total (h/sem)', 'Vínculo']],
                sort_action='native', filter_action='native', page_size=15,
                style_table={'overflowX': 'auto', 'borderRadius': '10px'},
                style_header={'backgroundColor': C['primary'], 'color': 'white',
                              'fontWeight': '600', 'fontSize': '0.85rem',
                              'border': f"1px solid {C['primary']}"},
                style_filter={'backgroundColor': C['lighter']},
                style_cell={'padding': '8px 14px', 'fontSize': '0.85rem',
                            'color': C['txt'], 'textAlign': 'left',
                            'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif',
                            'border': f"1px solid {C['lighter']}"},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']},
                    {'if': {'filter_query': '{Especialidade / Função} contains "Médico"'},
                     'fontWeight': '600', 'color': C['primary']},
                ],
            ),
        ], style=card()),

        # Recomendações automáticas
        html.Div([
            _sec_title("Recomendações Automáticas"),
            html.P("Geradas automaticamente a partir dos dados de carga horária, vínculos e "
                   "estrutura registrados no CNES.",
                   style={'fontSize': '0.84rem', 'color': C['txt2'], 'fontStyle': 'italic'}),
            html.Div([_rec_card(n, t, x) for n, t, x in poli_recomendacoes()]),
        ], style=card()),

        # Integração com o grafo
        html.Div([
            _sec_title("Integração com a Rede - Grafo de Proximidade"),
            html.P(f"A Policlínica (★) e suas conexões diretas no grafo de proximidade "
                   f"(unidades a menos de {THRESHOLD_KM}km). A unidade também aparece "
                   f"destacada na aba \"Mapa e Cobertura\" e no grafo de coloração da aba "
                   f"\"Visualização de Grafos\".",
                   style={'fontSize': '0.88rem', 'color': C['txt2'], 'lineHeight': '1.6'}),
            dcc.Graph(figure=fig_poli_ego(),
                      config={'displayModeBar': False}, style={'height': '480px'}),
        ], style=card()),

    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
], style={'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT: ANÁLISE DE CENÁRIOS "E SE?"
# ──────────────────────────────────────────────────────────
def scenario_df(mods):
    """Aplica as modificações do cenário (adições/remoções) ao dataset base."""
    mods = mods or {'add': [], 'remove': []}
    data = df[~df['Nome'].isin(mods.get('remove', []))].copy()
    for a in mods.get('add', []):
        coord = (float(a['lat']), float(a['lon']))
        bairro = min(CENTROIDES.index, key=lambda b: haversine(coord, CENTROIDES[b]))
        novo = {'Nome': a['nome'], 'Bairro': bairro, 'Categoria': a['cat'],
                'coord': coord,
                'Tipo': TIPO_SERVICO.get(a['cat'], 'Não-Emergencial')}
        data = pd.concat([data, pd.DataFrame([novo])], ignore_index=True)
    return data

def fig_scen_map(data, added=()):
    """Mapa de seleção do cenário: unidades atuais + grade clicável para
    capturar coordenadas de novas unidades."""
    fig = go.Figure()
    # grade transparente que captura cliques em área vazia
    glon = np.linspace(-43.45, -43.27, 46)
    glat = np.linspace(-4.95, -4.80, 38)
    gx, gy = np.meshgrid(glon, glat)
    fig.add_trace(go.Scatter(
        x=gx.ravel(), y=gy.ravel(), mode='markers',
        marker=dict(size=13, color='rgba(0,0,0,0)'),
        hovertemplate='Lat %{y:.5f} · Lon %{x:.5f}<br><i>clique para usar estas coordenadas</i><extra></extra>',
        showlegend=False,
    ))
    seen = set()
    for r in data.itertuples():
        is_new = r.Nome in added
        fig.add_trace(go.Scatter(
            x=[r.coord[1]], y=[r.coord[0]], mode='markers',
            marker=dict(size=16 if is_new else 9,
                        symbol='star' if is_new else 'circle',
                        color='#e9c46a' if is_new else CAT_COLORS.get(r.Categoria, C['secondary']),
                        line=dict(width=1.5, color='#1b4332')),
            text=[f"<b>{'★ ' if is_new else ''}{r.Nome}</b><br>{r.Categoria} - {r.Bairro}"],
            hovertemplate='%{text}<extra></extra>',
            name='★ Novas (cenário)' if is_new else r.Categoria,
            legendgroup='novo' if is_new else r.Categoria,
            showlegend=(('novo' if is_new else r.Categoria) not in seen),
        ))
        seen.add('novo' if is_new else r.Categoria)
    fig.update_layout(
        title=dict(text='Clique no mapa para capturar lat/lon · área urbana de Caxias',
                   font=dict(size=12, color=C['primary'])),
        xaxis=dict(title='Longitude', gridcolor='#e8f5e9', range=[-43.45, -43.27]),
        yaxis=dict(title='Latitude', gridcolor='#e8f5e9', range=[-4.95, -4.80],
                   scaleanchor='x', scaleratio=1),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', hovermode='closest',
        legend=dict(font=dict(size=9), x=1.01, y=1),
        margin=dict(l=50, r=150, t=40, b=40),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )
    return fig

def _delta(base, novo, fmt='{:.0f}', melhor='maior'):
    d = novo - base
    if abs(d) < 1e-9:
        return html.Span(' -', style={'color': C['txt2'], 'fontSize': '0.8rem'})
    bom = (d > 0) if melhor == 'maior' else (d < 0)
    return html.Span(f" {'▲' if d > 0 else '▼'} {fmt.format(abs(d))}",
                     style={'color': C['secondary'] if bom else C['danger'],
                            'fontSize': '0.8rem', 'fontWeight': '700'})

def render_comparacao(mods):
    """Comparação lado a lado: cenário atual × cenário simulado."""
    base = get_metricas_base()
    data = scenario_df(mods)
    cen = metricas_cenario(data)
    added = [a['nome'] for a in (mods or {}).get('add', [])]
    removed = (mods or {}).get('remove', [])

    linhas = [
        ('Unidades na rede', base['n'], cen['n'], '{:.0f}', 'maior'),
        ('UBS ativas', base['ubs'], cen['ubs'], '{:.0f}', 'maior'),
        ('Arestas (conflitos de proximidade)', base['arestas'], cen['arestas'], '{:.0f}', 'menor'),
        ('Número cromático χ (grupos p/ escalonamento)', base['chi'], cen['chi'], '{:.0f}', 'menor'),
        ('Grau médio do grafo', base['grau_medio'], cen['grau_medio'], '{:.2f}', 'menor'),
        (f'Índice de acessibilidade (% pop ≤ {RAIO_ACESSO_KM:g}km de UBS)',
         base['acess'], cen['acess'], '{:.1f}pp', 'maior'),
        ('Média de habitantes por UBS (Voronoi)', base['hab_ubs'], cen['hab_ubs'], '{:.0f}', 'menor'),
        ('UBS sobrecarregadas (> 4.000 hab)', base['sobrecarga'], cen['sobrecarga'], '{:.0f}', 'menor'),
    ]

    def _cell(v, fmt): return fmt.replace('pp', '').format(v)
    tab_cmp = html.Table([
        html.Thead(html.Tr([
            html.Th(h, style={'padding': '10px 14px', 'backgroundColor': C['primary'],
                              'color': 'white', 'fontSize': '0.85rem',
                              'textAlign': 'left' if h == 'Indicador' else 'center'})
            for h in ['Indicador', 'Cenário Atual', 'Cenário Simulado', 'Variação']
        ])),
        html.Tbody([
            html.Tr([
                html.Td(nome, style={'padding': '8px 14px', 'fontSize': '0.86rem', 'color': C['txt']}),
                html.Td(_cell(b, f), style={'padding': '8px 14px', 'textAlign': 'center',
                                            'fontWeight': '600', 'color': C['txt2']}),
                html.Td(_cell(n, f), style={'padding': '8px 14px', 'textAlign': 'center',
                                            'fontWeight': '700', 'color': C['primary']}),
                html.Td(_delta(b, n, f, m), style={'padding': '8px 14px', 'textAlign': 'center'}),
            ], style={'backgroundColor': 'white' if i % 2 == 0 else C['bg'],
                      'borderBottom': f"1px solid {C['lighter']}"})
            for i, (nome, b, n, f, m) in enumerate(linhas)
        ]),
    ], style={'width': '100%', 'borderCollapse': 'collapse'})

    def _alert_list(alertas):
        if not alertas:
            return html.P("Nenhuma UBS acima do parâmetro da PNAB.",
                          style={'color': C['secondary'], 'fontSize': '0.85rem'})
        return html.Ul([
            html.Li([html.Strong(a['nome'], style={
                        'color': C['danger'] if a['nivel'] == 'danger' else '#9a7b00'}),
                     html.Span(f" - {a['texto']}", style={'color': C['txt2']})],
                    style={'fontSize': '0.83rem', 'marginBottom': '6px'})
            for a in alertas
        ], style={'paddingLeft': '18px', 'margin': '0'})

    sug = sugerir_local_ubs(data)
    sug_div = html.Div([
        html.H4("Facility Location - Onde abrir a próxima UBS?",
                style={'color': C['primary'], 'marginTop': '0'}),
        (html.P([
            f"Sugestão (greedy, maximiza população coberta a ≤ {RAIO_ACESSO_KM:g}km): instalar UBS em ",
            html.Strong(sug['bairro']),
            f" (lat {sug['coord'][0]:.5f}, lon {sug['coord'][1]:.5f}) - cobriria ",
            html.Strong(f"{sug['ganho']:,} habitantes".replace(',', '.')),
            f" hoje descobertos. Bairros sem UBS a ≤ {RAIO_ACESSO_KM:g}km: "
            f"{', '.join(sug['descobertos'])}.",
        ], style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.7', 'margin': '0'})
         if sug else
         html.P("Toda a população está a ≤ 2km de uma UBS neste cenário - nenhuma "
                "instalação adicional necessária pelo critério de acessibilidade.",
                style={'color': C['secondary'], 'fontSize': '0.88rem', 'margin': '0'})),
    ], style={**card({'borderLeft': f"4px solid {C['accent']}"})})

    mods_txt = []
    if added:
        mods_txt.append(f"Adicionadas: {', '.join(added)}.")
    if removed:
        mods_txt.append(f"Removidas: {', '.join(removed)}.")

    return html.Div([
        html.P(' '.join(mods_txt) or 'Nenhuma modificação - cenário idêntico ao atual.',
               style={'color': C['primary'], 'fontWeight': '600', 'fontSize': '0.9rem'}),
        html.Div(tab_cmp, style=card()),
        html.Div([
            html.Div([
                html.H4("Grafo - Cenário Atual", style={'color': C['primary'], 'marginTop': '0'}),
                dcc.Graph(figure=fig_graph_coloring(base['G'], base['col']),
                          config={'displayModeBar': False}, style={'height': '420px'}),
                html.H5("Alertas de sobrecarga", style={'color': C['primary'], 'marginBottom': '6px'}),
                _alert_list(base['alertas']),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'marginBottom': '0'})}),
            html.Div([
                html.H4("Grafo - Cenário Simulado", style={'color': C['primary'], 'marginTop': '0'}),
                dcc.Graph(figure=fig_graph_coloring(cen['G'], cen['col']),
                          config={'displayModeBar': False}, style={'height': '420px'}),
                html.H5("Alertas de sobrecarga", style={'color': C['primary'], 'marginBottom': '6px'}),
                _alert_list(cen['alertas']),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),
        sug_div,
    ])

_scen_label = {'fontWeight': '600', 'color': C['primary'], 'fontSize': '0.85rem',
               'display': 'block', 'marginBottom': '4px', 'marginTop': '10px'}
_scen_input = {'width': '100%', 'padding': '7px 10px', 'border': f"1px solid {C['line']}",
               'fontSize': '0.88rem', 'boxSizing': 'border-box'}

tab_cenarios = html.Div([
    html.Div([
        html.H2('Análise de Cenários "E se?"', style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Simule intervenções na rede: adicione uma nova unidade (informe as coordenadas ou "
            "clique no mapa) ou remova unidades existentes. Ao simular, o grafo de proximidade, "
            "a coloração cromática, a cobertura Voronoi e os índices de acessibilidade são "
            "recalculados e comparados lado a lado com o cenário atual.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        html.Div([
            # Painel de edição
            html.Div([
                html.H4("➕ Adicionar unidade", style={'color': C['primary'], 'marginTop': '0',
                        'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px'}),
                html.Label("Nome", style=_scen_label),
                dcc.Input(id='scen-nome', type='text', placeholder='ex.: UBS NOVO HORIZONTE',
                          style=_scen_input),
                html.Label("Categoria", style=_scen_label),
                dcc.Dropdown(id='scen-cat',
                             options=[{'label': c, 'value': c} for c in sorted(CAT_COLORS)],
                             value='UBS', clearable=False, style={'fontSize': '0.88rem'}),
                html.Div([
                    html.Div([
                        html.Label("Latitude", style=_scen_label),
                        dcc.Input(id='scen-lat', type='number', placeholder='-4.86',
                                  style=_scen_input),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Label("Longitude", style=_scen_label),
                        dcc.Input(id='scen-lon', type='number', placeholder='-43.36',
                                  style=_scen_input),
                    ], style={'flex': '1'}),
                ], style={'display': 'flex', 'gap': '10px'}),
                html.Button("Adicionar ao cenário", id='btn-scen-add', n_clicks=0, style={
                    'marginTop': '14px', 'width': '100%', 'padding': '10px',
                    'backgroundColor': C['secondary'], 'color': 'white', 'border': 'none',
                    'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.9rem',
                }),

                html.H4("➖ Remover unidade", style={'color': C['primary'],
                        'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px',
                        'marginTop': '24px'}),
                dcc.Dropdown(id='scen-remove-sel',
                             options=[{'label': n, 'value': n} for n in sorted(df['Nome'])],
                             placeholder='Selecione a unidade…', style={'fontSize': '0.85rem'}),
                html.Button("Remover do cenário", id='btn-scen-remove', n_clicks=0, style={
                    'marginTop': '10px', 'width': '100%', 'padding': '10px',
                    'backgroundColor': C['danger'], 'color': 'white', 'border': 'none',
                    'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.9rem',
                }),

                html.H4("Modificações do cenário", style={'color': C['primary'],
                        'borderBottom': f"1px solid {C['line']}", 'paddingBottom': '8px',
                        'marginTop': '24px'}),
                html.Div(id='scen-mods-list',
                         children=html.P("Nenhuma modificação.",
                                         style={'color': C['txt2'], 'fontSize': '0.84rem'})),
                html.Div([
                    html.Button("Limpar", id='btn-scen-clear', n_clicks=0, style={
                        'flex': '1', 'padding': '10px', 'backgroundColor': C['lighter'],
                        'color': C['primary'], 'border': f"1px solid {C['line']}",
                        'fontWeight': '600', 'cursor': 'pointer',
                    }),
                    html.Button("▶ Simular Cenário", id='btn-simular', n_clicks=0, style={
                        'flex': '2', 'padding': '10px', 'backgroundColor': C['primary'],
                        'color': 'white', 'border': 'none', 'fontWeight': '700',
                        'cursor': 'pointer', 'fontSize': '0.95rem',
                    }),
                ], style={'display': 'flex', 'gap': '10px', 'marginTop': '14px'}),
            ], style={**card({'width': '330px', 'flexShrink': '0', 'marginBottom': '0'})}),

            # Mapa de seleção
            html.Div([
                dcc.Graph(id='scen-map', figure=fig_scen_map(df),
                          config={'displayModeBar': False},
                          style={'height': '640px'}),
            ], style={**card({'flex': '1', 'minWidth': '380px', 'padding': '10px',
                              'marginBottom': '0'})}),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        dcc.Loading(html.Div(id='scen-result'), type='circle', color=C['primary']),

    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}),
], style={'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'})


# ──────────────────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ──────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="Saúde Informada (Caxias-MA)",
                suppress_callback_exceptions=True,
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1'}])
server = app.server

app.layout = html.Div([
    html.Div([
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
    ], style=HDR),

    dcc.Store(id='sort-state', data={'col': 'n', 'asc': False}),
    dcc.Store(id='scen-mods', data={'add': [], 'remove': []}),

    dcc.Tabs(id='tabs', value='landing', children=[
        dcc.Tab(label='Início',              value='landing', style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Mapa e Cobertura',    value='mapa',    style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Visualização de Grafos', value='grafos', style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Cenários "E se?"',    value='cenarios', style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label='Estudo de Caso - Policlínica', value='policlinica', style=TAB_S, selected_style=TAB_SEL),
    ], style={'backgroundColor': C['white'], 'borderBottom': f"1px solid {C['line']}",
              'position': 'sticky', 'top': '0', 'zIndex': '999',
              'boxShadow': '0 2px 12px rgba(27,67,50,0.06)'}),

    html.Div(id='content'),

    html.Div([
        html.Div("Saúde Informada · IFMA Campus Caxias · PRPGI · 2025–2026",
                 style={'color': C['accent']}),
        html.Div("Dados: CNES/DATASUS · SUS · Coleta primária",
                 style={'color': C['accent'], 'fontSize': '0.83rem'}),
    ], style={
        'background': 'linear-gradient(120deg, #12291f 0%, #1b4332 55%, #1e5240 100%)',
        'borderTop': '1px solid rgba(82,183,136,0.45)', 'marginTop': '24px',
        'padding': '16px 40px', 'display': 'flex', 'justifyContent': 'space-between',
        'alignItems': 'center', 'fontSize': '0.88rem',
        'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif',
    }),
], style={'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif',
          'background': 'transparent', 'minHeight': '100vh'})


# ──────────────────────────────────────────────────────────
# CALLBACKS
# ──────────────────────────────────────────────────────────
def coverage_rows(fdf):
    rows = []
    for bairro, grp in fdf.groupby('Bairro'):
        n_u = len(grp)
        pop = POPULATION.get(bairro, 2000)
        ratio = (n_u / pop) * 1000
        pct = min(100.0, ratio * 20)
        if ratio >= 0.8:   status, sc = 'Adequada',   C['secondary']
        elif ratio >= 0.3: status, sc = 'Parcial',    C['warn']
        else:              status, sc = 'Deficiente',  C['danger']
        dem = DEMANDA.get(bairro, dict(atend=0, ocup=0.0, fila=0))
        rows.append(dict(bairro=bairro, pop=pop, n=n_u,
                         ratio=ratio, pct=pct, status=status, sc=sc,
                         atend=dem['atend'], ocup=dem['ocup'], fila=dem['fila']))
    return rows


@app.callback(Output('content', 'children'), Input('tabs', 'value'))
def render_tab(tab):
    if tab == 'landing':     return tab_landing
    if tab == 'mapa':        return tab_mapa
    if tab == 'grafos':      return tab_grafos
    if tab == 'cenarios':    return tab_cenarios
    if tab == 'policlinica': return tab_policlinica
    return html.Div()


@app.callback(
    Output('map-frame',   'srcDoc'),
    Output('map-summary', 'children'),
    Output('bar-chart',   'figure'),
    Output('pie-chart',   'figure'),
    Output('cov-table',   'children'),
    Input('filter-cat',   'value'),
    Input('filter-tipo',  'value'),
    Input('filter-busca', 'value'),
    Input('sort-state',   'data'),
)
def update_mapa(cat, tipo, busca, sort_state):
    busca = (busca or '').strip()
    fdf = df.copy()
    if cat != 'Todos':
        fdf = fdf[fdf['Categoria'] == cat]
    if tipo != 'Todos':
        fdf = fdf[fdf['Tipo'] == tipo]
    if busca:
        fdf = fdf[fdf['Nome'].str.contains(busca, case=False, na=False) |
                  fdf['Categoria'].str.contains(busca, case=False, na=False)]

    # Map
    map_html = make_map(cat, tipo, busca)

    # Summary
    tipo_badge = None
    if tipo != 'Todos':
        badge_color = C['danger'] if tipo == 'Emergencial' else C['secondary']
        tipo_badge = html.Div(
            tipo,
            style={
                'backgroundColor': badge_color, 'color': 'white',
                'fontSize': '0.72rem', 'fontWeight': '600', 'borderRadius': '999px',
                'padding': '3px 10px', 'marginTop': '6px', 'display': 'inline-block',
            }
        )
    summary = html.Div([
        html.Div([
            html.Span(str(len(fdf)), style={'fontSize': '2rem', 'fontWeight': '700',
                                            'color': C['primary'], 'display': 'block'}),
            html.Span("unidades", style={'fontSize': '0.78rem', 'color': C['txt2']}),
            tipo_badge,
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(str(fdf['Bairro'].nunique()), style={'fontSize': '1.5rem', 'fontWeight': '700',
                                                            'color': C['secondary'], 'display': 'block'}),
            html.Span("bairros", style={'fontSize': '0.78rem', 'color': C['txt2']}),
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(str(fdf['Categoria'].nunique()), style={'fontSize': '1.5rem', 'fontWeight': '700',
                                                               'color': C['accent'], 'display': 'block'}),
            html.Span("categorias", style={'fontSize': '0.78rem', 'color': C['txt2']}),
        ]),
    ])

    # Bar chart
    bc = fdf.groupby('Bairro').size().reset_index(name='n').nlargest(20, 'n')
    bar_fig = go.Figure(go.Bar(
        x=bc['Bairro'], y=bc['n'],
        marker_color=C['secondary'],
        hovertemplate='<b>%{x}</b><br>Unidades: %{y}<extra></extra>',
    ))
    bar_fig.update_layout(
        title=dict(text='Unidades por Bairro (Top 20)', font=dict(size=13, color=C['primary'])),
        xaxis=dict(tickangle=-45, gridcolor='#e8f5e9'),
        yaxis=dict(title='Unidades', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe',
        margin=dict(l=40, r=20, t=50, b=120),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif', color=C['txt']),
        showlegend=False,
    )

    # Pie chart
    pc = fdf['Categoria'].value_counts().reset_index()
    pc.columns = ['cat', 'n']
    pie_fig = go.Figure(go.Pie(
        labels=pc['cat'], values=pc['n'], hole=0.4,
        marker=dict(colors=[CAT_COLORS.get(c, C['secondary']) for c in pc['cat']]),
        textinfo='percent', textfont=dict(size=10),
    ))
    pie_fig.update_layout(
        showlegend=True, paper_bgcolor='white',
        legend=dict(font=dict(size=10), x=1.0),
        margin=dict(l=0, r=80, t=0, b=0),
        font=dict(family='Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'),
    )

    # Coverage table
    rows = coverage_rows(fdf)
    sort_col = (sort_state or {}).get('col', 'n')
    sort_asc = (sort_state or {}).get('asc', False)
    STATUS_ORDER = {'Adequada': 2, 'Parcial': 1, 'Deficiente': 0}

    def sort_key(x):
        v = x[sort_col]
        return STATUS_ORDER.get(v, 0) if sort_col == 'status' else v

    rows.sort(key=sort_key, reverse=not sort_asc)

    SORTABLE = {
        'Pop. (IBGE)': 'pop', 'Unidades': 'n',
        'Unid./1000 hab.': 'ratio', 'Atend./mês': 'atend',
        'Ocupação (%)': 'ocup', 'Fila estimada': 'fila',
        'Cobertura (%)': 'pct', 'Status': 'status',
    }

    def TH(txt):
        col_key = SORTABLE.get(txt)
        is_sorted = col_key is not None and sort_col == col_key
        arrow = (' ▲' if sort_asc else ' ▼') if is_sorted else ' ⇅'
        th_align = 'left' if txt == 'Bairro' else 'center' if txt == 'Status' else 'right'
        base = {
            'padding': '10px 14px', 'backgroundColor': C['primary'], 'color': 'white',
            'fontWeight': '600', 'fontSize': '0.85rem', 'whiteSpace': 'nowrap',
            'textAlign': th_align,
        }
        if col_key is None:
            return html.Th(txt, style=base)
        return html.Th(
            html.Button(
                [txt, html.Span(arrow, style={
                    'fontSize': '0.7rem', 'marginLeft': '4px',
                    'opacity': '1' if is_sorted else '0.55',
                })],
                id={'type': 'sort-col', 'col': col_key},
                n_clicks=0,
                style={
                    'background': 'none', 'border': 'none', 'color': 'white',
                    'fontWeight': '600', 'fontSize': '0.85rem', 'cursor': 'pointer',
                    'padding': '0', 'width': '100%', 'textAlign': th_align,
                },
            ),
            style=base,
        )

    def TD(txt, align='left', bold=False, color=None):
        return html.Td(txt, style={
            'padding': '8px 14px', 'fontSize': '0.85rem', 'textAlign': align,
            'fontWeight': '600' if bold else 'normal',
            'color': color or C['txt'],
        })

    table = html.Table([
        html.Thead(html.Tr([
            TH('Bairro'), TH('Pop. (IBGE)'), TH('Unidades'),
            TH('Unid./1000 hab.'), TH('Atend./mês'), TH('Ocupação (%)'),
            TH('Fila estimada'), TH('Cobertura (%)'), TH('Status'),
        ])),
        html.Tbody([
            html.Tr([
                TD(r['bairro']),
                TD(f"{r['pop']:,}".replace(',', '.'), align='right', color=C['txt2']),
                TD(str(r['n']), align='right', bold=True, color=C['primary']),
                TD(f"{r['ratio']:.3f}", align='right', color=C['txt2']),
                TD(f"{r['atend']:,}".replace(',', '.'), align='right', color=C['txt2']),
                TD(f"{r['ocup']:.0f}%", align='right', bold=r['ocup'] > 100,
                   color=C['danger'] if r['ocup'] > 100 else C['txt2']),
                TD(f"{r['fila']:,}".replace(',', '.'), align='right',
                   bold=r['fila'] > 0, color=C['danger'] if r['fila'] > 0 else C['txt2']),
                html.Td([
                    html.Div(style={'height': '6px', 'backgroundColor': C['lighter'],
                                    'borderRadius': '3px'}),
                    html.Div(style={
                        'height': '6px', 'backgroundColor': r['sc'],
                        'width': f"{r['pct']:.1f}%", 'marginTop': '-6px',
                        'borderRadius': '3px',
                    }),
                    html.Div(f"{r['pct']:.1f}%", style={
                        'fontSize': '0.78rem', 'color': C['txt2'],
                        'textAlign': 'right', 'marginTop': '3px',
                    }),
                ], style={'padding': '8px 14px', 'minWidth': '110px'}),
                html.Td(html.Span(r['status'], style={
                    'backgroundColor': r['sc'],
                    'color': 'white' if r['status'] != 'Parcial' else '#1b4332',
                    'padding': '3px 12px', 'fontSize': '0.78rem', 'fontWeight': '600',
                    'borderRadius': '999px',
                }), style={'padding': '8px 14px', 'textAlign': 'center'}),
            ], style={
                'backgroundColor': 'white' if i % 2 == 0 else C['bg'],
                'borderBottom': f"1px solid {C['lighter']}",
            })
            for i, r in enumerate(rows)
        ]),
    ], style={'width': '100%', 'borderCollapse': 'collapse',
              'fontFamily': 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'})

    return map_html, summary, bar_fig, pie_fig, table


@app.callback(
    Output('sort-state', 'data'),
    Input({'type': 'sort-col', 'col': ALL}, 'n_clicks'),
    State('sort-state', 'data'),
    prevent_initial_call=True,
)
def update_sort(n_clicks_list, current_sort):
    triggered = ctx.triggered_id
    if not triggered or not any(n or 0 for n in n_clicks_list):
        return current_sort or {'col': 'n', 'asc': False}
    col = triggered['col']
    current = current_sort or {'col': 'n', 'asc': False}
    if current['col'] == col:
        return {'col': col, 'asc': not current['asc']}
    return {'col': col, 'asc': True}


# ── Grafos dinâmicos (threshold + pesos) ─────────────────
@app.callback(
    Output('g-coloring', 'figure'),
    Output('g-force',    'figure'),
    Output('g-central',  'figure'),
    Output('g-sched',    'figure'),
    Output('graf-stats', 'children'),
    Input('graf-threshold', 'value'),
    Input('graf-pesos',     'value'),
)
def update_grafos(thr, pesos):
    com_pesos = 'pesos' in (pesos or [])
    Gt = build_graph(df, thr, com_pesos)
    col, chi = colorir(Gt)
    stats = html.Div([
        html.Div(f"χ = {chi}", style={'fontSize': '1.6rem',
                                      'fontFamily': '"JetBrains Mono", monospace'}),
        html.Div(f"{Gt.number_of_edges()} arestas · grau médio "
                 f"{np.mean([d for _, d in Gt.degree()]):.1f}",
                 style={'fontSize': '0.8rem', 'color': C['txt2'], 'fontWeight': '400'}),
    ])
    return (fig_graph_coloring(Gt, col, thr, com_pesos), fig_forceatlas2(Gt),
            fig_centralidade(Gt), fig_scheduling(Gt, col), stats)


# ── Cenários "E se?" ─────────────────────────────────────
@app.callback(
    Output('scen-lat', 'value'),
    Output('scen-lon', 'value'),
    Input('scen-map', 'clickData'),
    prevent_initial_call=True,
)
def scen_click(click_data):
    p = click_data['points'][0]
    return round(p['y'], 6), round(p['x'], 6)


@app.callback(
    Output('scen-mods',      'data'),
    Output('scen-mods-list', 'children'),
    Output('scen-map',       'figure'),
    Input('btn-scen-add',    'n_clicks'),
    Input('btn-scen-remove', 'n_clicks'),
    Input('btn-scen-clear',  'n_clicks'),
    State('scen-nome',       'value'),
    State('scen-cat',        'value'),
    State('scen-lat',        'value'),
    State('scen-lon',        'value'),
    State('scen-remove-sel', 'value'),
    State('scen-mods',       'data'),
    prevent_initial_call=True,
)
def scen_mods(n_add, n_rem, n_clr, nome, cat, lat, lon, remover, mods):
    mods = mods or {'add': [], 'remove': []}
    trig = ctx.triggered_id
    if trig == 'btn-scen-clear':
        mods = {'add': [], 'remove': []}
    elif trig == 'btn-scen-add' and lat is not None and lon is not None:
        nome = (nome or '').strip().upper() or f"NOVA UNIDADE {len(mods['add']) + 1}"
        if nome not in [a['nome'] for a in mods['add']]:
            mods['add'].append({'nome': nome, 'cat': cat or 'UBS',
                                'lat': float(lat), 'lon': float(lon)})
    elif trig == 'btn-scen-remove' and remover:
        if remover not in mods['remove']:
            mods['remove'].append(remover)

    itens = ([html.Li(f"➕ {a['nome']} ({a['cat']}) @ {a['lat']:.4f}, {a['lon']:.4f}",
                      style={'color': C['secondary'], 'fontSize': '0.82rem', 'marginBottom': '4px'})
              for a in mods['add']] +
             [html.Li(f"➖ {r}", style={'color': C['danger'], 'fontSize': '0.82rem',
                                        'marginBottom': '4px'})
              for r in mods['remove']])
    lista = (html.Ul(itens, style={'paddingLeft': '18px', 'margin': '0'}) if itens
             else html.P("Nenhuma modificação.",
                         style={'color': C['txt2'], 'fontSize': '0.84rem'}))
    data = scenario_df(mods)
    return mods, lista, fig_scen_map(data, added=[a['nome'] for a in mods['add']])


@app.callback(
    Output('scen-result', 'children'),
    Input('btn-simular', 'n_clicks'),
    State('scen-mods', 'data'),
    prevent_initial_call=True,
)
def simular_cenario(n, mods):
    return render_comparacao(mods)


# ── Exportações CSV ──────────────────────────────────────
@app.callback(
    Output('dl-cov', 'data'),
    Input('btn-export-cov', 'n_clicks'),
    prevent_initial_call=True,
)
def export_cov(n):
    rows = coverage_rows(df)
    out = pd.DataFrame(rows)[['bairro', 'pop', 'n', 'ratio', 'atend', 'ocup', 'fila', 'pct', 'status']]
    out.columns = ['Bairro', 'Populacao_IBGE', 'Unidades', 'Unid_por_1000hab',
                   'Atendimentos_Mes', 'Taxa_Ocupacao_pct', 'Fila_Estimada',
                   'Cobertura_pct', 'Status']
    return dcc.send_data_frame(out.to_csv, 'cobertura_por_bairro_caxias.csv', index=False)


@app.callback(
    Output('dl-poli', 'data'),
    Input('btn-export-poli', 'n_clicks'),
    prevent_initial_call=True,
)
def export_poli(n):
    out = df_poli[['Nome', 'Funcao', 'CH_Outro', 'CH_Amb', 'CH_Hosp', 'CH_Total', 'Vinculo']]
    return dcc.send_data_frame(out.to_csv,
                               f'profissionais_cnes_{POLI_CNES}.csv', index=False)


# ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
