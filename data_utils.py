"""Carga e limpeza dos dados: estabelecimentos de saúde (CSV de coleta
primária, georreferenciado) e ficha CNES da Policlínica de Caxias.

Todo o módulo é executado uma única vez na importação: os DataFrames
resultantes (`df_all`, `df_geo`) são o estado "base" do app, reaproveitado
por graph_utils e pelas abas.

Regras de limpeza aplicadas (decisões documentadas, sem inventar dados):
- Registros marcados como "(ANULADO)" no nome são excluídos por completo:
  representam serviço desativado, não uma lacuna de geolocalização.
- Registros sem coordenada válida (`NULL` na coleta) são mantidos na
  listagem de estabelecimentos, mas ficam fora do grafo espacial
  (não há como calcular distância sem coordenada) — sinalizados por
  `geo_valid=False`.
"""
import re
from pathlib import Path

import pandas as pd

from colors import COORD_LAT_RANGE, COORD_LON_RANGE

CSV_PATH = Path("Coleta Geolocalizacional de Dados Saúde Informada .csv")


# ──────────────────────────────────────────────────────────
# ESTABELECIMENTOS DE SAÚDE (coleta primária georreferenciada)
# ──────────────────────────────────────────────────────────
def parse_coord(s):
    if pd.isna(s) or str(s).strip().upper() in ('NULL', ''):
        return None
    m = re.search(r'-?\d+\.?\d*,\s*-?\d+\.?\d*', str(s))
    if not m:
        return None
    lat, lon = map(float, m.group(0).split(','))
    lat_min, lat_max = COORD_LAT_RANGE
    lon_min, lon_max = COORD_LON_RANGE
    if lat_min < lat < lat_max and lon_min < lon < lon_max:
        return (lat, lon)
    return None


def load_estabelecimentos():
    """Carrega o CSV de coleta primária e aplica a limpeza documentada
    no docstring do módulo."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de dados não encontrado: '{CSV_PATH}'. Verifique se o "
            "CSV de coleta geolocalizacional está na raiz do projeto."
        )
    raw = pd.read_csv(CSV_PATH)
    raw['Nome'] = raw['Nome'].str.strip()
    raw['Bairro'] = raw['Bairro'].str.strip()
    raw['Categoria'] = raw['Categoria'].str.strip()

    # exclui registros anulados/desativados (não são lacuna de dado)
    ativo = ~raw['Nome'].str.contains('ANULADO', case=False, na=False)
    out = raw.loc[ativo].drop(columns=['Localização no Google Maps']).reset_index(drop=True)

    out['coord'] = out['Coordenada de Localização'].apply(parse_coord)
    out['geo_valid'] = out['coord'].notna()
    return out


df_all = load_estabelecimentos()                 # todos os estabelecimentos ativos (75)
df_geo = df_all[df_all['geo_valid']].reset_index(drop=True)   # com coordenada válida → usado no grafo
CATEGORIAS = sorted(df_all['Categoria'].unique())

# ──────────────────────────────────────────────────────────
# FICHA CNES — AMBULATÓRIO ESPECIALIZADO DE CAXIAS / POLICLÍNICA
# (CNES 2453908, emitida 28/11/2025 — mesmo endereço/coordenada do
# registro "POLICLINICA DE CAXIAS" no CSV de coleta)
# ──────────────────────────────────────────────────────────
POLI_NOME_CSV = 'POLICLINICA DE CAXIAS'   # Nome como aparece no CSV de coleta
POLI_CNES = '2453908'

POLI_INFO = {
    'nome_fantasia_cnes': 'AMBULATORIO ESPECIALIZADO DE CAXIAS',
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

# Agregado por especialidade/função: nº de profissionais e soma de CH.
POLI_RESUMO_ESPECIALIDADES = (
    df_poli.groupby('Especialidade')
    .agg(n_profissionais=('Nome', 'count'), ch_total=('CH_Total', 'sum'))
    .reset_index()
    .sort_values('ch_total', ascending=False)
    .to_dict('records')
)

POLI_N_PROFISSIONAIS = len(df_poli)
POLI_N_MEDICOS = int(df_poli['Medico'].sum())
POLI_N_ESPECIALIDADES_MEDICAS = df_poli.loc[df_poli['Medico'], 'Especialidade'].nunique()
