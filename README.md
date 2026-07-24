# Saúde Informada

**Mapeamento e Análise dos Serviços de Saúde Pública em Caxias-MA**

Plataforma interativa que integra **dados geoespaciais validados** e **algoritmos de coloração de grafos** para revelar padrões de cobertura, redundâncias e lacunas na rede pública de saúde do município de Caxias-MA.

---

## Sobre o Projeto

O **Saúde Informada** é um projeto de pesquisa vinculado ao **PIBITI 2025/2026** (Programa Institucional de Bolsas de Iniciação em Desenvolvimento Tecnológico e Inovação) do **IFMA Campus Caxias**.

**Objetivo central:**  
Desenvolver uma plataforma que utiliza **teoria de grafos** para analisar criticamente a distribuição espacial dos serviços de saúde pública, identificando desigualdades regionais, redundâncias e vazios assistenciais.

O dataset foi construído a partir de dados oficiais do **CNES/DATASUS**, complementados com **verificação in loco via Google Maps**, garantindo alta confiabilidade georreferenciada.

---

### **Bolsista**
**Vinícius Yan Sousa Melo**

### **Orientador**
**Prof. Dr. Luis Fernando Maia Santos Silva**

**Programa:** PRPGI Nº 09/2025 — PIBITI ES 2025/2026 · IFMA Campus Caxias

---

## ✨ Funcionalidades

- **Mapa interativo** (Folium + Leaflet.js) com marcadores categorizados e controle de camadas
- **Grafo de proximidade geográfica** (threshold de 2 km) com coloração cromática
- **Visualização Force Layout** (Spring/ForceAtlas2) revelando topologia da rede
- **Diagrama de Voronoi** – regiões de influência de cada unidade de saúde
- **Coloração de grafos** para alocação otimizada de recursos (sem conflitos)
- **Tabela de cobertura por bairro** com índice (unidades/1.000 hab.) e classificação
- **Gráficos dinâmicos** (barras e pizza) filtráveis por tipo de serviço

---

## 🛠️ Stack Tecnológica

| Camada                    | Tecnologia                          | Versão     | Função |
|--------------------------|-------------------------------------|------------|--------|
| Framework Web            | **Dash (Plotly)** + Flask           | 2.x        | Dashboard interativo |
| Visualização             | **Plotly** + **Folium**             | 5.x / 0.14 | Gráficos e mapas |
| Análise de Grafos        | **NetworkX**                        | 3.x        | Grafo e coloração |
| Geoprocessamento         | **SciPy (Voronoi)** + **haversine** | -          | Distância e regiões |
| Processamento            | **Pandas** + **NumPy**              | 2.x / 1.24 | Dados e cálculos |

**Linguagem:** Python 3.10+

---

## Algoritmos e Métodos

- **Distância Geodésica**: Fórmula de Haversine (threshold = 2 km)
- **Coloração de Grafos**: `nx.greedy_color` com estratégia `largest_first`
- **Layout de Rede**: `nx.spring_layout` (aproximação ForceAtlas2)
- **Tesselação de Voronoi**: `scipy.spatial.Voronoi`
- **Índice de Cobertura**: `(n_unidades / população) × 1000` por bairro

---

## Fontes de Dados

- **CNES/DATASUS** (dados oficiais)
- **Google Maps** + verificação de campo
- **Coleta Geolocalizacional de Dados Saúde Informada.csv** (dataset principal)
- Estimativas populacionais por bairro (IBGE)

**Categorias incluídas**: UBS, UPA, SAMU, Hospital, CAPS, Centros Especializados, Ambulatórios, Diagnóstico, etc.

---

## Como Executar

### 1. Clone o repositório
```bash
git clone https://github.com/seuusuario/saude-informada.git
cd saude-informada
