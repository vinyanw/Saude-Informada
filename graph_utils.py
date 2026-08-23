"""Modelagem do grafo de proximidade espacial e cálculo de métricas de
conectividade por raio.

Cada estabelecimento com coordenada válida é um vértice; existe aresta
entre dois vértices quando a distância geodésica (haversine) entre eles
é ≤ ao raio testado. Este módulo é só computação (NetworkX/SciPy/
haversine) — a renderização de cada resultado vive nos módulos de aba.
"""
from functools import lru_cache

import networkx as nx
import numpy as np
from haversine import haversine
from scipy.spatial import cKDTree

from colors import RADII_KM
from data_utils import df_geo


def build_graph(data, radius_km):
    """Grafo de proximidade: pré-filtro de vizinhança com k-d tree
    (O(n log n)) e verificação haversine exata para cada par candidato."""
    G = nx.Graph()
    rows = list(data.itertuples())
    for r in rows:
        G.add_node(r.Nome, pos=r.coord, categoria=r.Categoria, bairro=r.Bairro)
    pts = np.array([r.coord for r in rows])
    if len(pts) >= 2:
        # raio em graus com folga (1° ≈ 111 km no equador)
        tree = cKDTree(pts)
        for i, j in tree.query_pairs(r=radius_km / 111.0 * 1.6):
            dist = haversine(rows[i].coord, rows[j].coord)
            if dist <= radius_km:
                G.add_edge(rows[i].Nome, rows[j].Nome, distance=dist)
    return G


@lru_cache(maxsize=16)
def build_graph_cached(radius_km):
    return build_graph(df_geo, radius_km)


# ──────────────────────────────────────────────────────────
# COLORAÇÃO
# ──────────────────────────────────────────────────────────
def colorir_greedy(G):
    """Coloração gulosa (greedy), estratégia 'largest_first' (ordena por grau)."""
    col = nx.greedy_color(G, strategy='largest_first')
    return col, (max(col.values()) + 1 if col else 0)


def colorir_dsatur(G):
    """Aproximação de DSATUR: prioriza nós de maior grau de saturação
    (nº de cores distintas já usadas nos vizinhos). NetworkX não tem
    DSATUR nativo — 'saturation_largest_first' é a estratégia equivalente
    disponível na biblioteca."""
    col = nx.greedy_color(G, strategy='saturation_largest_first')
    return col, (max(col.values()) + 1 if col else 0)


COLORING_STRATEGIES = {
    'Greedy (largest_first)': colorir_greedy,
    'DSATUR (aprox.)': colorir_dsatur,
}


def isolated_nodes(G):
    """Estabelecimentos sem nenhum vizinho dentro do raio — candidatos a
    'possível vazio assistencial' (não é conclusão isolada, ver métricas
    de componentes conexos e concentração antes de interpretar)."""
    return [n for n in G.nodes if G.degree(n) == 0]


# ──────────────────────────────────────────────────────────
# MÉTRICAS DE CONECTIVIDADE POR RAIO
# ──────────────────────────────────────────────────────────
def metricas_raio(radius_km, data=None):
    """Métricas de conectividade do grafo para um raio específico."""
    data = data if data is not None else df_geo
    G = build_graph(data, radius_km)
    graus = [d for _, d in G.degree()]
    componentes = list(nx.connected_components(G))
    isolados = isolated_nodes(G)
    _, n_cores_greedy = colorir_greedy(G)
    _, n_cores_dsatur = colorir_dsatur(G)
    return {
        'raio_km': radius_km,
        'n_vertices': G.number_of_nodes(),
        'n_arestas': G.number_of_edges(),
        'grau_medio': float(np.mean(graus)) if graus else 0.0,
        'n_isolados': len(isolados),
        'isolados': isolados,
        'n_componentes': len(componentes),
        'tamanho_maior_componente': max((len(c) for c in componentes), default=0),
        'n_cores_greedy': n_cores_greedy,
        'n_cores_dsatur': n_cores_dsatur,
    }


@lru_cache(maxsize=1)
def get_metricas_todos_raios():
    """Tabela de métricas para todos os raios testados (0.5/1/2/3/5 km),
    calculada uma única vez sob demanda."""
    return [metricas_raio(r) for r in RADII_KM]
