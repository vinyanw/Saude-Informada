"""Modelagem de grafo de proximidade, coloração cromática, cobertura
populacional (Voronoi/vizinho-mais-próximo), centralidade e facility
location.

Este módulo é só computação (NetworkX/SciPy/haversine) — a renderização
Plotly de cada resultado vive nos módulos de aba (`tabs/*.py`), que
importam as funções daqui e decidem como desenhar.
"""
from functools import lru_cache

import networkx as nx
import numpy as np
from haversine import haversine
from scipy.spatial import cKDTree

from colors import PNAB_LIMITE_ATENCAO, PNAB_LIMITE_CRITICO, RAIO_ACESSO_KM, THRESHOLD_KM
from data_utils import DEMANDA, POPULATION, df

# ──────────────────────────────────────────────────────────
# GRAFO DE PROXIMIDADE
# ──────────────────────────────────────────────────────────
def peso_aresta(t1, t2):
    """Peso de conflito da aresta por par de tipos de serviço: duas
    unidades emergenciais próximas concorrem mais fortemente por
    recursos do que um par misto (complementaridade emergência × AB)."""
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


@lru_cache(maxsize=16)
def build_graph_base_cached(threshold=THRESHOLD_KM, com_pesos=True):
    """Versão memoizada de build_graph() para o cenário base (df fixo):
    evita reconstruir o grafo a cada troca de aba/threshold já visto."""
    return build_graph(df, threshold=threshold, com_pesos=com_pesos)


# ──────────────────────────────────────────────────────────
# COLORAÇÃO CROMÁTICA — comparação entre estratégias
# ──────────────────────────────────────────────────────────
def colorir(Gt, strategy='largest_first'):
    """Coloração gulosa (greedy) do grafo. strategy segue as opções do
    NetworkX: 'largest_first' (DSATUR aproximado por grau) ou
    'connected_sequential' (ordem de travessia), entre outras."""
    col = nx.greedy_color(Gt, strategy=strategy)
    return col, (max(col.values()) + 1 if col else 0)


def colorir_dsatur(Gt):
    """Aproximação de DSATUR: prioriza nós de maior grau de saturação
    (nº de cores distintas já usadas nos vizinhos). NetworkX não tem
    DSATUR nativo — 'saturation_largest_first' é a estratégia mais
    próxima disponível na biblioteca."""
    col = nx.greedy_color(Gt, strategy='saturation_largest_first')
    return col, (max(col.values()) + 1 if col else 0)


def colorir_random(Gt, seed=42):
    """Coloração gulosa com ordem aleatória dos nós — baseline ingênuo
    para comparação com greedy/DSATUR (mostra o custo de não ordenar
    por grau/saturação)."""
    import random
    rnd = random.Random(seed)
    nodes = list(Gt.nodes())
    rnd.shuffle(nodes)
    col = {}
    for n in nodes:
        vizinhos_cores = {col[v] for v in Gt.neighbors(n) if v in col}
        c = 0
        while c in vizinhos_cores:
            c += 1
        col[n] = c
    return col, (max(col.values()) + 1 if col else 0)


COLORING_STRATEGIES = {
    'Greedy (largest_first)': colorir,
    'DSATUR (aprox.)': colorir_dsatur,
    'Aleatório': colorir_random,
}


def isolated_nodes(Gr):
    """Unidades sem nenhuma vizinha dentro do threshold do grafo —
    vazios assistenciais candidatos a análise de redundância zero."""
    return [n for n in Gr.nodes if Gr.degree(n) == 0]


# ──────────────────────────────────────────────────────────
# GRAFO E COLORAÇÃO BASE (cenário completo)
# ──────────────────────────────────────────────────────────
G = build_graph(df)
coloring, chromatic_n = colorir(G)

# ──────────────────────────────────────────────────────────
# COBERTURA POPULACIONAL — vizinho mais próximo / acessibilidade
# ──────────────────────────────────────────────────────────
# Centroides dos bairros (média das coordenadas das unidades de cada bairro);
# fixos no cenário base — cenários simulados alteram as unidades, não os bairros.
CENTROIDES = df.groupby('Bairro')['coord'].apply(
    lambda s: (float(np.mean([c[0] for c in s])), float(np.mean([c[1] for c in s]))))


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
        nivel = ('danger' if pop > PNAB_LIMITE_CRITICO else
                 'warn' if pop > PNAB_LIMITE_ATENCAO else None)
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
    vals = list(atribuida.values())
    graus = [d for _, d in Gt.degree()]
    return dict(
        n=len(data), ubs=int((data['Categoria'] == 'UBS').sum()),
        arestas=Gt.number_of_edges(), chi=chi,
        grau_medio=float(np.mean(graus)) if graus else 0.0,
        acess=indice_acessibilidade(data),
        hab_ubs=float(np.mean(vals)) if vals else 0.0,
        sobrecarga=sum(1 for v in vals if v > PNAB_LIMITE_ATENCAO),
        alertas=alertas_sobrecarga(data, Gt),
        G=Gt, col=col,
    )


_METRICAS_BASE_CACHE = None


def get_metricas_base():
    """Métricas do cenário base, calculadas uma única vez sob demanda."""
    global _METRICAS_BASE_CACHE
    if _METRICAS_BASE_CACHE is None:
        _METRICAS_BASE_CACHE = metricas_cenario(df)
    return _METRICAS_BASE_CACHE
