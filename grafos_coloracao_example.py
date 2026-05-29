import pandas as pd
import networkx as nx
from haversine import haversine
import folium
from folium import plugins
import webbrowser
from pathlib import Path
import re
from scipy.spatial import KDTree
import numpy as np

# ====================== CONFIGURAÇÕES ======================
CSV_PATH = Path("Coleta Geolocalizacional de Dados Saúde Informada .csv")
THRESHOLD_KM = 2.0
MAP_OUTPUT = "mapa_saude_caxias_categorias.html"

# ====================== 1. CARREGAR E LIMPAR DADOS ======================
def parse_coordinates(coord_str):
    if pd.isna(coord_str) or str(coord_str).strip() in ['NULL', '']:
        return None
    try:
        # Remove texto extra (ex: " (aprox...)")
        match = re.search(r'-?\d+\.?\d*,\s*-?\d+\.?\d*', str(coord_str))
        if match:
            lat, lon = map(float, match.group(0).split(','))
            # Validação aproximada para Caxias-MA
            if -5.5 < lat < -4.5 and -44.0 < lon < -42.5:
                return (lat, lon)
    except:
        pass
    return None

df = pd.read_csv(CSV_PATH)

# Limpeza
df['Coordenada de Localização'] = df['Coordenada de Localização'].astype(str)
df['coord'] = df['Coordenada de Localização'].apply(parse_coordinates)
df = df.dropna(subset=['coord']).reset_index(drop=True)

print(f"Total de estabelecimentos com coordenadas válidas: {len(df)}")

# ====================== 2. CONSTRUIR GRAFO ======================
def build_graph(positions, threshold_km=2.0):
    G = nx.Graph()
    coords = np.array(list(positions.values()))
    names = list(positions.keys())
    
    # KDTree para eficiência
    tree = KDTree(coords)
    
    for i, name in enumerate(names):
        G.add_node(name, 
                   pos=positions[name], 
                   categoria=df.loc[df['Nome'] == name, 'Categoria'].values[0],
                   bairro=df.loc[df['Nome'] == name, 'Bairro'].values[0])
        
        # Busca vizinhos próximos
        indices = tree.query_ball_point(coords[i], r=threshold_km/111.32)  # conversão aproximada km→graus
        for j in indices:
            if i < j:
                dist = haversine(positions[names[i]], positions[names[j]])
                G.add_edge(names[i], names[j], distance=dist)
    return G

positions = dict(zip(df['Nome'], df['coord']))

print("\n=== Construindo grafo ===")
G = build_graph(positions, THRESHOLD_KM)

# Coloração de grafos
coloring = nx.greedy_color(G, strategy='largest_first')
chromatic_number = max(coloring.values()) + 1 if coloring else 0

print(f"Número cromático (com limiar {THRESHOLD_KM}km): {chromatic_number}")
print(f"Nós isolados: {len(list(nx.isolates(G)))}")

# ====================== 3. MAPA INTERATIVO COM CAMADAS POR CATEGORIA ======================
m = folium.Map(location=[-4.865, -43.36], zoom_start=13, tiles="CartoDB positron")

# Cores por categoria
category_colors = {
    "UBS": "blue",
    "UPA": "red",
    "SAMU": "orange",
    "Hospital": "darkred",
    "Maternidade": "pink",
    "CAPS": "purple",
    "Centro Especializado": "green",
    "Ambulatório / Especializado": "cadetblue",
    "Policlínica / Ambulatório": "lightblue",
    "Diagnóstico": "gray",
    "Ambulatório": "lightgreen",
    "Clínica Especializada": "beige"
}

# Adicionar marcadores por camada
feature_groups = {}

for cat in df['Categoria'].unique():
    feature_groups[cat] = folium.FeatureGroup(name=cat, show=True)

for node in G.nodes():
    data = G.nodes[node]
    lat, lon = data['pos']
    cat = data['categoria']
    cor = category_colors.get(cat, "black")
    
    popup_html = f"""
    <b>{node}</b><br>
    Bairro: {data['bairro']}<br>
    Categoria: {cat}<br>
    Cor do Grafo: {coloring.get(node, 0)}
    """
    
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=cor, icon="plus", prefix="fa")
    ).add_to(feature_groups[cat])

# Adicionar as camadas ao mapa
for fg in feature_groups.values():
    fg.add_to(m)

# Adicionar conexões (arestas)
for u, v in G.edges():
    lat1, lon1 = G.nodes[u]['pos']
    lat2, lon2 = G.nodes[v]['pos']
    folium.PolyLine(
        locations=[[lat1, lon1], [lat2, lon2]],
        weight=1.5,
        color="gray",
        opacity=0.4
    ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
plugins.Fullscreen().add_to(m)

# Salvar e abrir
m.save(MAP_OUTPUT)
print(f"\nMapa salvo em: {MAP_OUTPUT}")

webbrowser.open(f"file://{Path(MAP_OUTPUT).absolute()}")