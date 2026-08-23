"""Design system: paleta de cores e constantes geográficas compartilhadas
por todos os módulos do app.
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
MAP_CENTER = (-4.865, -43.36)
COORD_LAT_RANGE = (-5.5, -4.5)   # validação de coordenadas coletadas (parse_coord)
COORD_LON_RANGE = (-44.0, -42.5)

# ──────────────────────────────────────────────────────────
# GRAFO DE PROXIMIDADE ESPACIAL
# ──────────────────────────────────────────────────────────
RADII_KM = [0.5, 1.0, 2.0, 3.0, 5.0]   # raios testados para a construção do grafo
DEFAULT_RADIUS_KM = 2.0                 # raio padrão exibido no mapa/análise
