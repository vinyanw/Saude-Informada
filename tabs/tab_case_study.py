"""Aba 8 — Estudo de Caso: Ambulatório Especializado de Caxias (CNES 2453908).

Ficha técnica, carga horária por especialidade, tabela de profissionais,
recomendações automáticas e integração com o grafo de proximidade.
"""
import networkx as nx
import plotly.graph_objects as go
from dash import Input, Output, dash_table, dcc, html

from colors import C, CAT_COLORS, CHROM_PALETTE, THRESHOLD_KM
from components import card, export_csv_button, info_card, kpi, rec_card
from data_utils import (
    N_EQUIPAMENTOS,
    N_ESPECIALIDADES,
    POLI_EQUIPAMENTOS,
    POLI_INFO,
    POLI_INSTALACOES,
    POLI_CNES,
    POLI_NOME,
    TOTAL_H_MEDICAS,
    _COOP,
    _CT,
    df_med,
    df_poli,
)
from graph_utils import G

FONT = 'Inter, "Helvetica Neue", Helvetica, Arial, sans-serif'


def _sec_title(txt):
    return html.H3(txt, style={'color': C['primary'], 'marginTop': '0',
                               'borderBottom': f"1px solid {C['line']}",
                               'borderLeft': f"3px solid {C['accent']}",
                               'paddingLeft': '12px', 'letterSpacing': '-0.01em', 'paddingBottom': '10px'})


def poli_recomendacoes():
    """Recomendações automáticas derivadas dos dados do CNES."""
    recs = []
    esp = df_med.groupby('Especialidade').agg(ch=('CH_Total', 'sum'), n=('Nome', 'count'))

    baixa = esp[esp['ch'] < 20].sort_values('ch')
    for e, r in baixa.iterrows():
        recs.append(('danger' if r['ch'] <= 10 else 'warn', f"Baixa oferta em {e}",
                     f"Apenas {int(r['ch'])}h/semana ({int(r['n'])} médico(s)). Considerar ampliação "
                     f"de carga horária ou contratação - oferta inferior a 20h/sem limita o acesso "
                     f"via regulação."))

    unicos = esp[esp['n'] == 1]
    if len(unicos):
        nomes_unicos = ', '.join(unicos.index)
        recs.append(('warn', "Especialidades com profissional único",
                     f"{nomes_unicos}: a oferta depende de um único médico - férias ou desligamento "
                     f"interrompem o serviço. Avaliar redundância mínima."))

    ch_hosp = df_poli[df_poli['CH_Hosp'] > 0]
    for _, r in ch_hosp.iterrows():
        recs.append(('warn', "Carga horária hospitalar em unidade ambulatorial",
                     f"{r['Nome']} ({r['Funcao']}) tem {r['CH_Hosp']}h registradas como hospitalares "
                     f"em estabelecimento exclusivamente ambulatorial - verificar consistência do "
                     f"cadastro no CNES."))

    coop = df_med[df_med['Vinculo'] == _COOP]
    pct_coop = len(coop) / len(df_med) * 100
    if pct_coop > 20:
        recs.append(('warn', "Dependência de vínculos intermediados",
                     f"{len(coop)} de {len(df_med)} médicos ({pct_coop:.0f}%) atuam como cooperados/"
                     f"intermediados, vínculo de menor estabilidade para a rede."))

    temp = df_poli[df_poli['Vinculo'] == _CT]
    recs.append(('info', "Vínculos temporários predominantes",
                 f"{len(temp)} de {len(df_poli)} profissionais ({len(temp)/len(df_poli)*100:.0f}%) "
                 f"têm contrato por prazo determinado. Alta rotatividade potencial compromete a "
                 f"continuidade assistencial."))

    media_esp = TOTAL_H_MEDICAS / max(1, N_ESPECIALIDADES)
    recs.append(('info', "Funcionamento 24h vs. oferta médica concentrada",
                 f"A unidade registra atendimento contínuo 24h/dia (168h/sem), mas a oferta média é "
                 f"de apenas {media_esp:.0f}h semanais por especialidade ({TOTAL_H_MEDICAS}h ÷ "
                 f"{N_ESPECIALIDADES} especialidades) - divulgar a grade de horários por "
                 f"especialidade evita demanda frustrada fora da escala."))
    return recs


def fig_ch_especialidade():
    """Barras horizontais empilhadas: CH semanal por especialidade, um segmento por médico."""
    esp_total = df_med.groupby('Especialidade')['CH_Total'].sum().sort_values()
    ordem = esp_total.index.tolist()
    fig = go.Figure()
    for i, (_, r) in enumerate(df_med.sort_values('CH_Total', ascending=False).iterrows()):
        fig.add_trace(go.Bar(
            y=[r['Especialidade']], x=[r['CH_Total']], orientation='h',
            marker=dict(color=CHROM_PALETTE[i % len(CHROM_PALETTE)], line=dict(width=1, color='white')),
            text=[f"<b>{r['Nome']}</b><br>{r['Funcao']}<br>CH amb.: {r['CH_Amb']}h · "
                  f"CH total: {r['CH_Total']}h/sem<br>Vínculo: {r['Vinculo']}"],
            hovertemplate='%{text}<extra></extra>', showlegend=False,
        ))
    for esp, total in esp_total.items():
        fig.add_annotation(y=esp, x=total, text=f" {int(total)}h", showarrow=False, xanchor='left',
                           font=dict(size=11, color=C['primary']))
    fig.update_layout(
        barmode='stack',
        title=dict(text='Carga Horária Semanal por Especialidade Médica (cada segmento = um médico)',
                   font=dict(size=13, color=C['primary'])),
        yaxis=dict(categoryorder='array', categoryarray=ordem, tickfont=dict(size=11)),
        xaxis=dict(title='Horas/semana', gridcolor='#e8f5e9'),
        paper_bgcolor='white', plot_bgcolor='#f8fffe', margin=dict(l=10, r=60, t=50, b=40), font=dict(family=FONT),
    )
    return fig


def fig_poli_ego():
    """Subgrafo de vizinhança da Policlínica no grafo de proximidade."""
    if POLI_NOME not in G.nodes:
        return go.Figure()
    ego = nx.ego_graph(G, POLI_NOME, radius=1)
    pos = nx.spring_layout(ego, k=1.5, iterations=100, seed=7)
    ex, ey = [], []
    for u, v in ego.edges():
        x1, y1 = pos[u]; x2, y2 = pos[v]
        ex += [x1, x2, None]; ey += [y1, y2, None]
    traces = [go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=1, color='#b7e4c7'),
                         hoverinfo='none', showlegend=False)]
    for n in ego.nodes():
        is_poli = (n == POLI_NOME)
        cat = ego.nodes[n]['categoria']
        traces.append(go.Scatter(
            x=[pos[n][0]], y=[pos[n][1]], mode='markers',
            marker=dict(size=26 if is_poli else 12, symbol='star' if is_poli else 'circle',
                        color='#e9c46a' if is_poli else CAT_COLORS.get(cat, C['secondary']),
                        line=dict(width=2 if is_poli else 1.5, color='#1b4332')),
            text=[f"<b>{'★ ' if is_poli else ''}{n}</b><br>Categoria: {cat}<br>Bairro: {ego.nodes[n]['bairro']}"],
            hovertemplate='%{text}<extra></extra>', showlegend=False,
        ))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text=f'Vizinhança no Grafo de Proximidade - {G.degree(POLI_NOME)} unidades a ≤ {THRESHOLD_KM}km',
                   font=dict(size=13, color=C['primary'])),
        hovermode='closest', paper_bgcolor='white', plot_bgcolor='#f8fffe',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=60, b=20), font=dict(family=FONT),
    )
    return fig


def layout():
    return html.Div([
        html.H2("Análise Detalhada: Ambulatório Especializado de Caxias (CNES 2453908)",
                style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(f"Estudo de caso a partir da Ficha de Estabelecimento CNES/DATASUS "
               f"(emitida em 28/11/2025) · {len(df_poli)} profissionais cadastrados · unidade "
               f"destacada com ★ no mapa e no grafo de proximidade.",
               style={'color': C['txt2'], 'marginBottom': '24px'}),

        html.Div([
            kpi(f"{TOTAL_H_MEDICAS}h", "horas médicas semanais", C['primary']),
            kpi(N_ESPECIALIDADES, "especialidades médicas", C['secondary']),
            kpi(N_EQUIPAMENTOS, "equipamentos em uso (SUS)", C['accent']),
            kpi(len(df_poli), "profissionais no CNES", C['warn']),
            kpi(11, "consultórios especializados", C['danger']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        html.Div([
            info_card("📍 Endereço e Contato",
                       html.P(POLI_INFO['endereco'], style={'color': C['txt2'], 'fontSize': '0.88rem',
                                                            'lineHeight': '1.7', 'margin': '0'}), C['primary']),
            info_card("🏥 Tipo de Estabelecimento",
                       html.P(POLI_INFO['tipo'], style={'color': C['txt2'], 'fontSize': '0.88rem',
                                                        'lineHeight': '1.7', 'margin': '0'}), C['secondary']),
            info_card("⚕️ Nível de Atenção",
                       html.P(POLI_INFO['nivel'], style={'color': C['txt2'], 'fontSize': '0.88rem',
                                                         'lineHeight': '1.7', 'margin': '0'}), C['accent']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '16px'}),

        html.Div([
            info_card("🩺 Serviços Principais",
                       html.Ul([html.Li(s, style={'marginBottom': '5px'}) for s in POLI_INFO['servicos']],
                               style={'color': C['txt2'], 'fontSize': '0.86rem', 'lineHeight': '1.6',
                                      'paddingLeft': '18px', 'margin': '0'}), C['primary']),
            info_card("🕐 Horário de Funcionamento",
                       html.Div([
                           html.P(POLI_INFO['horario'], style={'color': C['txt2'], 'fontSize': '0.88rem',
                                                               'lineHeight': '1.7', 'marginTop': '0'}),
                           html.P("Fluxo de clientela: demanda espontânea e referenciada.",
                                  style={'color': C['txt2'], 'fontSize': '0.85rem', 'fontStyle': 'italic', 'margin': '0'}),
                       ]), C['warn']),
            info_card("🔬 Equipamentos e Instalações",
                       html.Div([
                           html.P(" · ".join(f"{n} ({q})" for n, q in POLI_EQUIPAMENTOS),
                                  style={'color': C['txt2'], 'fontSize': '0.86rem', 'lineHeight': '1.7', 'marginTop': '0'}),
                           html.P(" · ".join(f"{n}: {q}" for n, q in POLI_INSTALACOES),
                                  style={'color': C['txt2'], 'fontSize': '0.82rem', 'margin': '0'}),
                       ]), C['secondary']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '20px'}),

        html.Div([
            _sec_title("Carga Horária por Especialidade Médica"),
            dcc.Graph(figure=fig_ch_especialidade(), config={'displayModeBar': False}, style={'height': '480px'}),
        ], style=card()),

        html.Div([
            _sec_title("Profissionais Cadastrados no CNES"),
            html.Div([
                html.P("Tabela interativa: ordene clicando no cabeçalho e filtre digitando nas caixas "
                       "abaixo dos títulos das colunas.",
                       style={'fontSize': '0.84rem', 'color': C['txt2'], 'fontStyle': 'italic', 'margin': '0'}),
                export_csv_button('btn-export-poli', 'dl-poli'),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                      'gap': '12px', 'marginBottom': '10px'}),
            dash_table.DataTable(
                data=df_poli[['Nome', 'Funcao', 'CH_Amb', 'CH_Total', 'Vinculo']]
                    .rename(columns={'Funcao': 'Especialidade / Função', 'CH_Amb': 'CH Ambulatorial (h/sem)',
                                     'CH_Total': 'CH Total (h/sem)', 'Vinculo': 'Vínculo'}).to_dict('records'),
                columns=[{'name': c, 'id': c} for c in
                         ['Nome', 'Especialidade / Função', 'CH Ambulatorial (h/sem)', 'CH Total (h/sem)', 'Vínculo']],
                sort_action='native', filter_action='native', page_size=15,
                style_table={'overflowX': 'auto', 'borderRadius': '10px'},
                style_header={'backgroundColor': C['primary'], 'color': 'white', 'fontWeight': '600',
                              'fontSize': '0.85rem', 'border': f"1px solid {C['primary']}"},
                style_filter={'backgroundColor': C['lighter']},
                style_cell={'padding': '8px 14px', 'fontSize': '0.85rem', 'color': C['txt'], 'textAlign': 'left',
                            'fontFamily': FONT, 'border': f"1px solid {C['lighter']}"},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': C['bg']},
                    {'if': {'filter_query': '{Especialidade / Função} contains "Médico"'},
                     'fontWeight': '600', 'color': C['primary']},
                ],
            ),
        ], style=card()),

        html.Div([
            _sec_title("Recomendações Automáticas"),
            html.P("Geradas automaticamente a partir dos dados de carga horária, vínculos e estrutura "
                   "registrados no CNES.", style={'fontSize': '0.84rem', 'color': C['txt2'], 'fontStyle': 'italic'}),
            html.Div([rec_card(n, t, x) for n, t, x in poli_recomendacoes()]),
        ], style=card()),

        html.Div([
            _sec_title("Integração com a Rede - Grafo de Proximidade"),
            html.P(f"A Policlínica (★) e suas conexões diretas no grafo de proximidade (unidades a "
                   f"menos de {THRESHOLD_KM}km). A unidade também aparece destacada na aba \"Mapa "
                   f"Interativo\" e no grafo de coloração da aba \"Análise de Grafos\".",
                   style={'fontSize': '0.88rem', 'color': C['txt2'], 'lineHeight': '1.6'}),
            dcc.Graph(figure=fig_poli_ego(), config={'displayModeBar': False}, style={'height': '480px'}),
        ], style=card()),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output('dl-poli', 'data'),
        Input('btn-export-poli', 'n_clicks'),
        prevent_initial_call=True,
    )
    def export_poli(n):
        out = df_poli[['Nome', 'Funcao', 'CH_Outro', 'CH_Amb', 'CH_Hosp', 'CH_Total', 'Vinculo']]
        return dcc.send_data_frame(out.to_csv, f'profissionais_cnes_{POLI_CNES}.csv', index=False)
