import networkx as nx
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import re
from collections import Counter
import time
import folium
from networkx.algorithms import community

start_time = time.time()

# === CARREGA OS DADOS ===
df = pd.read_csv('Coleta Geolocalizacional de Dados Saúde Informada .csv') 

def parse_coordinates(coord_str):
    if pd.isna(coord_str) or str(coord_str).strip().upper() == 'NULL':
        return None
    s = str(coord_str).strip().strip('"').replace('(aprox. de fontes online)', '').strip()
    matches = re.findall(r'[-]?\d+\.\d+', s)
    if len(matches) >= 2:
        try:
            return (float(matches[0]), float(matches[1]))
        except:
            return None
    return None

df['coords'] = df['Coordenada de Localização'].apply(parse_coordinates)
df_valid = df[df['coords'].notna()].copy()
print(f"Estabelecimentos válidos: {len(df_valid)}")

positions = {}
bairro_dict = {}
for _, row in df_valid.iterrows():
    name = row['Nome']
    positions[name] = row['coords']
    bairro_dict[name] = row['Bairro']

# === FUNÇÃO HAVERSINE ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Raio da Terra em km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# === ANÁLISE COM VÁRIOS THRESHOLDS ===
thresholds = [1.0, 1.5, 2.0, 3.0, 5.0]

print("\n=== ANÁLISE COM DIFERENTES DISTÂNCIAS MÁXIMAS ===")

for thresh in thresholds:
    print(f"\n--- Threshold = {thresh} km ---")
    
    G_temp = nx.Graph()
    for h in positions:
        G_temp.add_node(h, pos=positions[h], bairro=bairro_dict.get(h, 'Desconhecido'))
    
    for i in list(G_temp.nodes):
        for j in list(G_temp.nodes):
            if i != j and haversine(*G_temp.nodes[i]['pos'], *G_temp.nodes[j]['pos']) < thresh:
                G_temp.add_edge(i, j)
    
    coloring_temp = nx.greedy_color(G_temp, strategy='largest_first')
    chrom = max(coloring_temp.values()) + 1 if coloring_temp else 0
    avg_degree = sum(dict(G_temp.degree()).values()) / len(G_temp) if len(G_temp) > 0 else 0
    num_components = nx.number_connected_components(G_temp)
    isolated_count = len(list(nx.isolates(G_temp)))
    
    print(f"Nós: {len(G_temp)} | Arestas: {G_temp.number_of_edges()} | Componentes: {num_components}")
    print(f"Número cromático: {chrom}")
    print(f"Grau médio: {avg_degree:.2f}")
    print(f"Isolados: {isolated_count}")

# === GRAFO PRINCIPAL (threshold 2 km) para mapa e comunidades ===
print("\n=== GRAFO PRINCIPAL (threshold fixo 2 km) para visualização e comunidades ===")

G = nx.Graph()
for h in positions:
    G.add_node(h, pos=positions[h], bairro=bairro_dict.get(h, 'Desconhecido'))

for i in list(G.nodes):
    for j in list(G.nodes):
        if i != j and haversine(*G.nodes[i]['pos'], *G.nodes[j]['pos']) < 2.0:
            G.add_edge(i, j)

# Coloração final
coloring = nx.greedy_color(G, strategy='largest_first')
chrom = max(coloring.values()) + 1 if coloring else 0
avg_degree = sum(dict(G.degree()).values()) / len(G) if len(G) > 0 else 0
num_components = nx.number_connected_components(G)
isolated = list(nx.isolates(G))

print(f"Nós: {len(G)} | Arestas: {G.number_of_edges()} | Componentes: {num_components}")
print(f"Número cromático: {chrom}")
print(f"Grau médio: {avg_degree:.2f}")
print(f"Isolados: {len(isolated)}")

# Distribuição por bairro
print("\nPor bairro:")
for b, c in sorted(Counter(df_valid['Bairro']).items(), key=lambda x: (-x[1], x[0])):
    print(f"  {b}: {c}")

print("\nIsolados (prioridade para novas UBS):")
for iso in isolated:
    print(f"  - {iso} ({bairro_dict.get(iso, 'N/A')})")

# === MAPA COM FOLIUM ===
m = folium.Map(location=[-4.865, -43.36], zoom_start=12, tiles='CartoDB positron')

colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'pink', 
          'darkblue', 'darkgreen', 'gray', 'black', 'lightblue', 'lightgreen', 
          'beige', 'darkpurple', 'lightgray', 'darkcyan', 'cyan', 'lime', 
          'magenta', 'brown', 'darkorange', 'olive', 'teal']

for node in G.nodes():
    lat, lon = G.nodes[node]['pos']
    color_idx = coloring.get(node, 0) % len(colors)
    folium.Marker(
        location=[lat, lon],
        popup=f"{node}<br>Bairro: {G.nodes[node]['bairro']}<br>Cor: {coloring.get(node, '?')}",
        icon=folium.Icon(color=colors[color_idx], icon='info-sign')
    ).add_to(m)

for u, v in G.edges():
    lat1, lon1 = G.nodes[u]['pos']
    lat2, lon2 = G.nodes[v]['pos']
    folium.PolyLine([[lat1, lon1], [lat2, lon2]], color="gray", weight=1, opacity=0.3).add_to(m)

m.save("mapa_saude_caxias_colored.html")
print("Mapa salvo como: mapa_saude_caxias_colored.html → abra no navegador!")

# === DETECÇÃO DE COMUNIDADES (LOUVAIN) ===
print("\n=== COMUNIDADES DETECTADAS (Louvain) ===")

communities = community.louvain_communities(G)

print(f"Total de comunidades: {len(communities)}")

for idx, comm in enumerate(communities, 1):
    if len(comm) == 0:
        continue
    bairros = set(G.nodes[n]['bairro'] for n in comm)
    nomes = sorted(comm)
    print(f"\nComunidade {idx} ({len(comm)} serviços):")
    print(f"  Bairros: {', '.join(sorted(bairros))}")
    if len(nomes) > 0:
        print(f"  Exemplos: {', '.join(nomes[:5])}{'...' if len(nomes) > 5 else ''}")

print(f"\nTempo total de execução: {time.time() - start_time:.2f} segundos")