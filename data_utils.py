"""Carga e preparação de dados: unidades de saúde (CSV de coleta primária),
população oficial (IBGE), demanda assistencial (SIA/DATASUS ou estimativa
MS) e dados de referência do estudo de caso da Policlínica (CNES).

Todo o módulo é executado uma única vez na importação: os DataFrames e
dicts resultantes (`df`, `POPULATION`, `DEMANDA`, ...) são o estado
"base" do app, reaproveitado por graph_utils e pelas abas.
"""
import gzip
import json
import re
import urllib.request
from pathlib import Path

import pandas as pd

from colors import COORD_LAT_RANGE, COORD_LON_RANGE, TIPO_SERVICO, CONSULTAS_HAB_ANO, CAPACIDADE_UNIDADE_MES

CSV_PATH = Path("Coleta Geolocalizacional de Dados Saúde Informada .csv")

# ──────────────────────────────────────────────────────────
# POPULAÇÃO POR BAIRRO (estimativa calibrada pela coleta primária)
# ──────────────────────────────────────────────────────────
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
# DEMANDA ASSISTENCIAL (SIA/DATASUS ou estimativa MS)
# ──────────────────────────────────────────────────────────
# Se existir um arquivo 'demanda_sia.csv' (export do TabNet/SIA com colunas
# Bairro, Atendimentos_Mes, Taxa_Ocupacao, Fila_Espera), ele é usado como
# fonte real. Na ausência, a demanda é estimada por parâmetros assistenciais
# do Ministério da Saúde (Portaria 1.631/2015: ~2,8 consultas/hab/ano).
DEMANDA_CSV = Path('demanda_sia.csv')


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
# UNIDADES DE SAÚDE (coleta primária georreferenciada)
# ──────────────────────────────────────────────────────────
def parse_coord(s):
    if pd.isna(s) or str(s).strip() in ('NULL', ''):
        return None
    m = re.search(r'-?\d+\.?\d*,\s*-?\d+\.?\d*', str(s))
    if m:
        lat, lon = map(float, m.group(0).split(','))
        lat_min, lat_max = COORD_LAT_RANGE
        lon_min, lon_max = COORD_LON_RANGE
        if lat_min < lat < lat_max and lon_min < lon < lon_max:
            return (lat, lon)
    return None


def load_unidades():
    """Carrega o CSV de coleta primária, valida coordenadas e enriquece
    com o Tipo de serviço (Emergencial / Não-Emergencial)."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de dados não encontrado: '{CSV_PATH}'. Verifique se o "
            "CSV de coleta geolocalizacional está na raiz do projeto."
        )
    df_raw = pd.read_csv(CSV_PATH)
    df_raw['coord'] = df_raw['Coordenada de Localização'].apply(parse_coord)
    df_out = df_raw.dropna(subset=['coord']).reset_index(drop=True)
    df_out['Tipo'] = df_out['Categoria'].map(TIPO_SERVICO).fillna('Não-Emergencial')
    return df_out


df = load_unidades()
UNIDADES_POR_BAIRRO = df.groupby('Bairro').size().to_dict()
DEMANDA, DEMANDA_FONTE = build_demanda(POPULATION, UNIDADES_POR_BAIRRO)
CAT_BY_NOME = df.set_index('Nome')['Categoria'].to_dict()

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
df_poli['Especialidade'] = (df_poli['Funcao']
                             .str.replace('Médico em ', '', regex=False)
                             .str.replace('Médico ', '', regex=False))

df_med = df_poli[df_poli['Medico']].copy()
TOTAL_H_MEDICAS = int(df_med['CH_Total'].sum())
N_ESPECIALIDADES = df_med['Especialidade'].nunique()
N_EQUIPAMENTOS = sum(q for _, q in POLI_EQUIPAMENTOS)
