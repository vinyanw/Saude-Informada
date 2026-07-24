"""Design system: paleta de cores e constantes geográficas/regulatórias
compartilhadas por todos os módulos do app.

Fonte única de verdade para valores antes hardcoded em múltiplos pontos
do app.py original (centro do mapa, limite PNAB, thresholds de grafo).
"""

# ──────────────────────────────────────────────────────────
# PALETA PRINCIPAL (design system)
# ──────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────
# PALETAS CATEGÓRICAS
# ──────────────────────────────────────────────────────────
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

CHROM_PALETTE = [
    '#2d6a4f', '#e76f51', '#e9c46a', '#4361ee',
    '#9b5de5', '#f4acb7', '#4cc9f0', '#95d5b2', '#ff9f1c', '#2ec4b6',
]

# ──────────────────────────────────────────────────────────
# GEOGRAFIA — CAXIAS-MA
# ──────────────────────────────────────────────────────────
MAP_CENTER = (-4.865, -43.36)          # centro usado por make_map, fig_voronoi, fig_scen_map
COORD_LAT_RANGE = (-5.5, -4.5)         # validação de coordenadas coletadas (parse_coord)
COORD_LON_RANGE = (-44.0, -42.5)

# ──────────────────────────────────────────────────────────
# GRAFO DE PROXIMIDADE
# ──────────────────────────────────────────────────────────
THRESHOLD_KM = 1.0                     # threshold padrão do grafo global
THRESHOLDS_KM = [1.0, 2.0, 5.0]        # opções expostas no slider/radio de grafos e mapa
RAIO_ACESSO_KM = 2.0                   # raio usado no índice de acessibilidade (~30 min a pé)

# ──────────────────────────────────────────────────────────
# PARÂMETROS ASSISTENCIAIS (PNAB — Política Nacional de Atenção Básica)
# ──────────────────────────────────────────────────────────
PNAB_LIMITE_ATENCAO = 4000    # hab. de influência por UBS acima do qual soa alerta "atenção"
PNAB_LIMITE_CRITICO = 8000    # hab. de influência por UBS acima do qual soa alerta "crítico"

# ──────────────────────────────────────────────────────────
# ESTIMATIVA DE DEMANDA (Portaria MS 1.631/2015, fallback sem SIA/DATASUS)
# ──────────────────────────────────────────────────────────
CONSULTAS_HAB_ANO = 2.8
CAPACIDADE_UNIDADE_MES = 704   # 4 atend/h × 8h × 22 dias úteis
