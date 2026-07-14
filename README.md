# Saúde Informada — Mapeamento e Análise dos Serviços de Saúde Pública em Caxias-MA

> Plataforma interativa que integra dados geoespaciais validados a algoritmos de coloração de grafos para revelar padrões de cobertura, redundâncias e lacunas na rede pública de saúde do município de Caxias-MA.

**Programa:** PRPGI Nº 09/2025 — PIBITI ES 2025/2026 · IFMA Campus Caxias  
**Bolsista:** Vinícius Yan Sousa Melo  
**Orientador:** Prof. Dr. Luis Fernando Maia Santos Silva

---

## Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Stack Tecnológica](#stack-tecnológica)
- [Algoritmos e Métodos](#algoritmos-e-métodos)
- [Fontes de Dados](#fontes-de-dados)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Executar](#como-executar)
- [Referências](#referências)
- [Agradecimentos](#agradecimentos)

---

## Sobre o Projeto

O **Saúde Informada** é um projeto de pesquisa vinculado ao PIBITI (Programa Institucional de Bolsas de Iniciação em Desenvolvimento Tecnológico e Inovação) do IFMA Campus Caxias. O objetivo central é desenvolver uma plataforma que aplique a **teoria de coloração de grafos** para analisar criticamente a distribuição dos serviços de saúde pública em Caxias-MA, identificando desigualdades regionais, redundâncias e vazios assistenciais.

O dataset foi coletado e validado a partir do **CNES/DATASUS** e verificação in loco via **Google Maps**, abrangendo UBS, hospitais, CAPS, UPA, SAMU, centros especializados, ambulatórios e serviços de diagnóstico do município.

---

## Funcionalidades

- **Mapa interativo** (Folium/Leaflet.js) com marcadores por categoria e controle de camadas
- **Grafo de proximidade geográfica** com coloração cromática (threshold 2 km)
- **Rede ForceAtlas2/Spring** que revela a topologia de conexões independente da posição geográfica
- **Diagrama de Voronoi** com regiões de influência por unidade de saúde
- **Coloração para alocação de recursos** — grupos sem conflito para escalonamento de serviços
- **Tabela de cobertura por bairro** com índice unidades/1000 hab. e status (Adequada / Parcial / Deficiente)
- **Gráficos dinâmicos** (barras e pizza) filtráveis por tipo de serviço

---

## Stack Tecnológica

### Framework Web

| Biblioteca | Versão mínima | Função no projeto |
|---|---|---|
| [Dash (Plotly)](https://dash.plotly.com/) | 2.x | Framework principal para construção do dashboard interativo em Python. Gerencia o roteamento de abas, callbacks reativos e serve a aplicação via Flask. |
| [Flask](https://flask.palletsprojects.com/) | — | Servidor WSGI embutido no Dash; exposto via `app.server` para possível deploy em produção. |

### Visualização de Dados

| Biblioteca | Versão mínima | Função no projeto |
|---|---|---|
| [Plotly](https://plotly.com/python/) (`plotly.graph_objects`) | 5.x | Geração de gráficos interativos: scatter de grafo geográfico, grafo force-layout, diagrama de Voronoi, barras e pizza. Todos com hover, zoom e exportação. |
| [Folium](https://python-visualization.github.io/folium/) | 0.14.x | Mapa interativo baseado em Leaflet.js. Renderiza marcadores categorizados, arestas do grafo como polylines e controle de camadas por tipo de serviço. |
| [Folium Plugins](https://python-visualization.github.io/folium/plugins.html) | — | Plugin `Fullscreen` para expansão do mapa em tela cheia. |

### Análise de Grafos

| Biblioteca | Versão mínima | Função no projeto |
|---|---|---|
| [NetworkX](https://networkx.org/) | 3.x | Construção do grafo de proximidade (vértices = unidades de saúde; arestas = distância ≤ 2 km). Executa o algoritmo de coloração greedy (`largest_first`) e o spring layout para visualização de força. |

### Processamento de Dados

| Biblioteca | Versão mínima | Função no projeto |
|---|---|---|
| [Pandas](https://pandas.pydata.org/) | 2.x | Leitura e limpeza do dataset CSV. Filtragem por categoria, agrupamentos por bairro e cálculo de métricas de cobertura. |
| [NumPy](https://numpy.org/) | 1.24.x | Operações matriciais sobre coordenadas geográficas para a tesselação de Voronoi. |

### Geometria e Distância Geográfica

| Biblioteca | Versão mínima | Função no projeto |
|---|---|---|
| [haversine](https://pypi.org/project/haversine/) | 2.x | Cálculo da distância geodésica (em km) entre dois pares de coordenadas GPS. Usado para definir adjacências no grafo (threshold 2 km). |
| [SciPy](https://scipy.org/) (`scipy.spatial.Voronoi`) | 1.10.x | Geração da tesselação de Voronoi sobre as coordenadas das unidades da área urbana central de Caxias, delimitando regiões de influência geográfica. |

### Linguagem e Utilitários

| Recurso | Versão | Função no projeto |
|---|---|---|
| Python | 3.10+ | Linguagem de desenvolvimento. |
| `re` (stdlib) | — | Extração de coordenadas numéricas de strings via expressão regular. |
| `pathlib.Path` (stdlib) | — | Manipulação de caminhos de arquivo de forma portável. |

---

## Algoritmos e Métodos

### 1. Haversine para Grafo de Proximidade

A distância entre cada par de unidades de saúde é calculada pela **fórmula de haversine**, que considera a curvatura da Terra e retorna a distância geodésica em km. Uma aresta é adicionada ao grafo se a distância for ≤ 2 km (threshold configurável em `THRESHOLD_KM`).

```
d = 2r · arcsin(√(sin²(Δlat/2) + cos(lat₁)·cos(lat₂)·sin²(Δlon/2)))
```

### 2. Coloração Greedy de Grafos (`nx.greedy_color`)

Implementado via NetworkX com estratégia `largest_first` (os vértices de maior grau são coloridos primeiro). O algoritmo atribui a cada vértice a menor cor não utilizada por seus vizinhos, produzindo o **número cromático χ** — quantidade mínima de grupos sem conflito de adjacência.

**Aplicação prática:** unidades no mesmo grupo de cor podem receber o mesmo tipo de recurso (equipe, insumo, turno) sem sobreposição dentro do raio de 2 km.

### 3. Spring Layout (aproximação ForceAtlas2)

`nx.spring_layout` é um algoritmo de layout dirigido por forças (Fruchterman-Reingold), usado como aproximação do ForceAtlas2. Nós conectados são atraídos; não conectados são repelidos. O layout resultante revela clusters e a topologia da rede independente da posição geográfica real.

### 4. Diagrama de Voronoi (`scipy.spatial.Voronoi`)

A tesselação de Voronoi divide o plano em regiões, onde cada região contém todos os pontos mais próximos de uma determinada unidade de saúde do que de qualquer outra. Usada para identificar:
- Gaps de cobertura (polígonos muito grandes sem serviços internos)
- Sobreposição/redundância (polígonos muito pequenos, serviços muito concentrados)

### 5. Índice de Cobertura por Bairro

Calculado como `(n_unidades / população_estimada) × 1000`, produzindo um indicador de **unidades por 1.000 habitantes** por bairro. Classificado em:
- **Adequada:** ≥ 0,8 unid./1.000 hab.
- **Parcial:** ≥ 0,3 e < 0,8
- **Deficiente:** < 0,3

---

## Fontes de Dados

| Fonte | Tipo | Uso |
|---|---|---|
| **CNES/DATASUS** — [cnes.datasus.gov.br](http://cnes.datasus.gov.br) | Dados oficiais | Listagem primária dos estabelecimentos de saúde cadastrados em Caxias-MA (nome, tipo, endereço). |
| **Google Maps** | Verificação geoespacial | Validação e geolocalização (lat/lon) das unidades coletadas no CNES, com verificação in loco. |
| **Coleta primária** | Dataset próprio | Arquivo `Coleta Geolocalizacional de Dados Saúde Informada .csv` — resultado da integração e validação manual das duas fontes anteriores. Contém: Nome, Bairro, Categoria e Coordenada de Localização. |
| **Estimativas populacionais por bairro** | Estimativa | Valores estimados manualmente com base em dados históricos do IBGE para cada bairro/localidade de Caxias-MA, usados no cálculo do índice de cobertura. |

### Categorias de Estabelecimentos

O dataset cobre os seguintes tipos de serviço:

`UBS` · `UPA` · `SAMU` · `Hospital` · `Maternidade` · `CAPS` · `CAPS / Acolhimento` · `Centro Especializado` · `Ambulatório / Especializado` · `Policlínica / Ambulatório` · `Diagnóstico` · `Ambulatório` · `Clínica Especializada`

---

## Estrutura do Projeto

```
Saude-Informada/
├── app.py                                        # Aplicação principal (Dash)
├── grafos_coloracao_example.py                   # Script Folium standalone (versão anterior)
├── mapa_saude_caxias_categorias.html             # Mapa exportado estático
├── Coleta Geolocalizacional de Dados Saúde Informada .csv   # Dataset principal
├── Relatório Parcial Saúde Informada.md          # Relatório científico parcial (PIBITI)
├── assets/
│   └── style.css                                 # Estilos CSS globais do Dash
└── README.md
```

---

## Como Executar

### 1. Pré-requisitos

Python 3.10 ou superior instalado.

### 2. Instalar dependências

```bash
pip install dash plotly pandas networkx numpy folium haversine scipy
```

### 3. Executar a aplicação

```bash
python app.py
```

A aplicação estará disponível em: `http://localhost:8050`

> O arquivo CSV de dados deve estar na mesma pasta que `app.py`.

---

## Referências

AURENHAMMER, Franz; KLEIN, Rolf; LEE, Der-Tsai. **Voronoi Diagrams and Delaunay Triangulations.** Singapore: World Scientific, 2013.

BRASIL. Ministério da Saúde. **Cadastro Nacional de Estabelecimentos de Saúde (CNES).** Disponível em: <http://cnes.datasus.gov.br>. Acesso em: 5 jul. 2026.

DABIRE, Inoussa et al. **Health Centers Network Analysis with Gephi and ForceAtlas2.** 2025.

JENSEN, Tommy R.; TOFT, Bjarne. **Graph Coloring Problems.** New York: Wiley-Interscience, 1995.

LEWIS, Rhyd. **Graph Colouring: A Visual Tour.** arXiv, 2026. Disponível em: <https://arxiv.org/>. Acesso em: 5 jul. 2026.

MARX, Daniel. Graph Coloring Problems and Their Applications in Scheduling. **Periodica Polytechnica Electrical Engineering,** v. 48, n. 1-2, p. 11-16, 2004.

NETWORKX DEVELOPERS. **NetworkX: Network Analysis in Python.** Disponível em: <https://networkx.org>. Acesso em: 5 jul. 2026.

OKABE, Atsuyuki et al. **Spatial Tessellations: Concepts and Applications of Voronoi Diagrams.** 2. ed. Chichester: John Wiley & Sons, 2000.

---

## Agradecimentos

- **IFMA** — Instituto Federal do Maranhão, Campus Caxias, pelo suporte institucional e infraestrutura de pesquisa
- **PRPGI** — Pró-Reitoria de Pesquisa, Pós-Graduação e Inovação, pelo apoio ao desenvolvimento científico no IFMA
- **SUS / DATASUS** — Pela disponibilização pública dos dados de saúde via CNES
- **Prof. Dr. Luis Fernando Maia Santos Silva** — Pela orientação, dedicação e suporte ao longo de toda a pesquisa
