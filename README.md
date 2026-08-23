# Saúde Informada

**Distribuição Espacial dos Serviços Públicos de Saúde de Caxias-MA via Teoria dos Grafos**

Plataforma que modela os estabelecimentos de saúde pública de Caxias-MA como um grafo de proximidade geodésica, para evidenciar concentrações e possíveis vazios assistenciais na rede.

---

## Sobre o Projeto

O **Saúde Informada** é um projeto de pesquisa vinculado ao **PIBITI 2025/2026** (Programa Institucional de Bolsas de Iniciação em Desenvolvimento Tecnológico e Inovação) do **IFMA Campus Caxias**.

**Pergunta central:**
Como a distribuição espacial dos serviços públicos de saúde de Caxias-MA pode ser analisada por meio da teoria dos grafos e apresentada em uma plataforma informativa para evidenciar concentrações e possíveis vazios assistenciais?

O dataset principal foi construído por coleta primária georreferenciada (verificação in loco via Google Maps). Um estabelecimento — a Policlínica de Caxias (CNES 2453908) — teve seus dados de recursos (profissionais, carga horária, serviços, equipamentos) complementados a partir da ficha oficial do CNES/DATASUS.

---

### **Bolsista**
**Vinícius Yan Sousa Melo**

### **Orientador**
**Prof. Dr. Luis Fernando Maia Santos Silva**

**Programa:** PRPGI Nº 09/2025 — PIBITI ES 2025/2026 · IFMA Campus Caxias

---

## Telas da Plataforma

1. **Visão Geral** — pergunta central, objetivos, metodologia e glossário de termos
2. **Mapa** — estabelecimentos, conexões do grafo e coloração cromática, com filtro de raio (0,5 a 5km) e categoria
3. **Análise da Rede** — métricas de conectividade por raio (vértices, arestas, grau médio, isolados, componentes conexos, coloração) e interpretação cautelosa dos resultados
4. **Lista de Estabelecimentos** — busca, detalhes de localização/categoria, estabelecimentos próximos e, para a Policlínica, o bloco de recursos extraído do CNES

---

## Metodologia

- **Limpeza de dados**: registros anulados/desativados são excluídos; estabelecimentos sem coordenada válida ficam de fora do grafo mas permanecem listados.
- **Grafo espacial**: cada estabelecimento com coordenada válida é um vértice; existe aresta entre dois vértices quando a distância geodésica (**Haversine**) entre eles é ≤ ao raio testado.
- **Raios testados**: 0,5 / 1 / 2 / 3 / 5 km — para cada um são calculados nº de vértices/arestas, grau médio, vértices isolados, componentes conexos e coloração.
- **Coloração de grafos**: `nx.greedy_color` com estratégias `largest_first` (greedy) e `saturation_largest_first` (aproximação de DSATUR).
- **Interpretação**: a coloração isolada não indica se a distribuição é boa ou ruim — é sempre cruzada com isolamento, fragmentação em componentes e concentração geográfica, com linguagem cautelosa ("possível vazio assistencial").

---

## Stack Tecnológica

| Camada                    | Tecnologia                          | Função |
|--------------------------|---------------------------------------|--------|
| Framework Web            | **Dash (Plotly)** + Flask             | Dashboard interativo |
| Visualização             | **Folium**                            | Mapa interativo |
| Análise de Grafos        | **NetworkX**                          | Grafo e coloração |
| Geoprocessamento         | **SciPy (cKDTree)** + **haversine**    | Distância e pré-filtro de vizinhança |
| Processamento            | **Pandas** + **NumPy**                | Dados e cálculos |

**Linguagem:** Python 3.10+

---

## Fontes de Dados

- Coleta primária georreferenciada (verificação em campo via Google Maps)
- **CNES/DATASUS** — ficha da Policlínica de Caxias (CNES 2453908)

**Categorias incluídas**: UBS, UPA, SAMU, Hospital, CAPS, Centros Especializados, Ambulatórios, Diagnóstico, etc.

---

## Como Executar

### 1. Clone o repositório
```bash
git clone https://github.com/seuusuario/saude-informada.git
cd saude-informada
```

### 2. Instale as dependências
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Rode a aplicação
```bash
python3 app.py
```

Acesse `http://127.0.0.1:8050`.
