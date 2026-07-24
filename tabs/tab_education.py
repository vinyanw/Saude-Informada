"""Aba 6 — Módulo Educativo (SUS).

Conteúdo interativo sobre o Sistema Único de Saúde: princípios, níveis
de atenção, direitos do usuário, como usar o Meu SUS Digital e um
mini-quiz de fixação. Conteúdo redigido com base na Lei 8.080/1990, na
Lei 8.142/1990 e em publicações institucionais do Ministério da Saúde.
"""
from dash import ALL, Input, Output, State, dcc, html

from colors import C
from components import card

QUIZ = [
    {
        'pergunta': 'O SUS é financiado e utilizado exclusivamente por quem paga plano de saúde privado?',
        'opcoes': ['Verdadeiro', 'Falso'],
        'correta': 'Falso',
        'explicacao': 'O SUS é de acesso universal e gratuito a qualquer pessoa no território '
                      'nacional, independentemente de contribuição prévia ou plano privado (art. 196 '
                      'da Constituição Federal).',
    },
    {
        'pergunta': 'Qual nível de atenção é a "porta de entrada" preferencial do SUS, responsável '
                    'por ações de prevenção e cuidado contínuo (ex.: UBS)?',
        'opcoes': ['Atenção Primária', 'Atenção Secundária', 'Atenção Terciária'],
        'correta': 'Atenção Primária',
        'explicacao': 'A Atenção Primária à Saúde (APS), prestada principalmente pelas UBS, é o '
                      'primeiro contato do usuário com o sistema e coordena o cuidado ao longo da '
                      'rede (Política Nacional de Atenção Básica).',
    },
    {
        'pergunta': 'Hospitais de média/alta complexidade e centros especializados (ex.: cirurgias, '
                    'UTI) correspondem a qual nível de atenção?',
        'opcoes': ['Atenção Primária', 'Atenção Secundária e Terciária'],
        'correta': 'Atenção Secundária e Terciária',
        'explicacao': 'A atenção secundária cobre especialidades e exames de média complexidade; a '
                      'terciária cobre procedimentos de alta complexidade — ambas normalmente '
                      'acessadas por encaminhamento da atenção primária.',
    },
    {
        'pergunta': 'O Meu SUS Digital permite consultar carteira de vacinação e histórico de '
                    'atendimentos pelo celular?',
        'opcoes': ['Verdadeiro', 'Falso'],
        'correta': 'Verdadeiro',
        'explicacao': 'O aplicativo/portal Meu SUS Digital, do Ministério da Saúde, centraliza '
                      'carteira de vacinação, histórico de atendimentos, resultados de exames e '
                      'agendamentos disponíveis na rede pública.',
    },
]


def _principio_card(titulo, texto, cor):
    return html.Div([
        html.H4(titulo, style={'color': C['primary'], 'marginTop': '0', 'marginBottom': '8px'}),
        html.P(texto, style={'color': C['txt2'], 'fontSize': '0.88rem', 'lineHeight': '1.6', 'margin': '0'}),
    ], className='hover-card',
       style={**card({'flex': '1', 'minWidth': '240px', 'borderTop': f'3px solid {cor}', 'marginBottom': '0'})})


def _nivel_card(nivel, exemplos, descricao, cor):
    return html.Div([
        html.Div(nivel, style={'fontWeight': '700', 'color': cor, 'fontSize': '1.05rem', 'marginBottom': '6px'}),
        html.P(descricao, style={'color': C['txt2'], 'fontSize': '0.87rem', 'lineHeight': '1.6', 'marginBottom': '8px'}),
        html.Div([
            html.Span(ex, style={
                'backgroundColor': C['bg'], 'color': C['primary'], 'fontSize': '0.76rem',
                'padding': '3px 10px', 'borderRadius': '999px', 'marginRight': '6px', 'marginBottom': '6px',
                'display': 'inline-block', 'border': f"1px solid {C['light']}",
            }) for ex in exemplos
        ]),
    ], className='hover-card', style={**card({'flex': '1', 'minWidth': '260px',
                                              'borderLeft': f'4px solid {cor}', 'marginBottom': '0'})})


def _direitos():
    direitos = [
        "Acesso universal e igualitário às ações e serviços de saúde, sem discriminação.",
        "Atendimento humanizado, acolhedor e livre de qualquer discriminação.",
        "Identificação do profissional responsável pelo seu cuidado.",
        "Consentimento livre e esclarecido antes de procedimentos, salvo risco iminente de morte.",
        "Acesso ao prontuário e às informações sobre seu próprio estado de saúde.",
        "Segunda opinião médica e direito a recusar tratamento.",
        "Confidencialidade das informações pessoais e de saúde.",
        "Participação social: usuários e comunidade participam do controle social do SUS "
        "(Conselhos e Conferências de Saúde, Lei 8.142/1990).",
    ]
    return html.Div([
        html.H3("Direitos do Usuário do SUS", style={
            'color': C['primary'], 'marginTop': '0', 'borderBottom': f"1px solid {C['line']}",
            'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px',
        }),
        html.Ul([html.Li(d, style={'marginBottom': '8px', 'lineHeight': '1.6'}) for d in direitos],
                style={'color': C['txt2'], 'paddingLeft': '20px', 'margin': '0'}),
    ], style=card())


def _meu_sus_digital():
    passos = [
        ("1. Baixe ou acesse", "Aplicativo \"Meu SUS Digital\" (Android/iOS) ou o portal "
         "meusus.saude.gov.br pelo navegador."),
        ("2. Entre com a conta gov.br", "O login usa sua conta gov.br (mesmo CPF cadastrado no "
         "Cadastro Nacional de Usuários do SUS)."),
        ("3. Consulte seus dados", "Carteira de vacinação, histórico de atendimentos, resultados "
         "de exames e agendamentos disponíveis na rede pública."),
        ("4. Agende ou acompanhe", "Em municípios com integração, é possível ver filas e "
         "agendamentos de consultas/exames pelo mesmo aplicativo."),
    ]
    return html.Div([
        html.H3("Como Usar o Meu SUS Digital", style={
            'color': C['primary'], 'marginTop': '0', 'borderBottom': f"1px solid {C['line']}",
            'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px',
        }),
        html.Div([
            html.Div([
                html.Strong(titulo, style={'color': C['primary'], 'display': 'block', 'marginBottom': '4px'}),
                html.Span(texto, style={'color': C['txt2'], 'fontSize': '0.87rem', 'lineHeight': '1.6'}),
            ], style={'flex': '1', 'minWidth': '220px', 'padding': '10px 14px',
                       'borderLeft': f"1px solid {C['line']}"})
            for titulo, texto in passos
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
    ], style=card())


def _quiz_pergunta(i, item):
    return html.Div([
        html.P(f"{i + 1}. {item['pergunta']}", style={'fontWeight': '600', 'color': C['primary'], 'marginBottom': '10px'}),
        dcc.RadioItems(
            id={'type': 'quiz-opt', 'index': i},
            options=[{'label': f' {op}', 'value': op} for op in item['opcoes']],
            style={'color': C['txt2'], 'fontSize': '0.9rem', 'display': 'flex',
                   'flexDirection': 'column', 'gap': '4px'},
        ),
        html.Div(id={'type': 'quiz-feedback', 'index': i}, style={'marginTop': '8px', 'fontSize': '0.85rem'}),
    ], style={'marginBottom': '20px', 'paddingBottom': '16px', 'borderBottom': f"1px solid {C['line']}"})


def _quiz():
    return html.Div([
        html.H3("Quiz Rápido: Você Conhece o SUS?", style={
            'color': C['primary'], 'marginTop': '0', 'borderBottom': f"1px solid {C['line']}",
            'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px',
        }),
        html.Div([_quiz_pergunta(i, item) for i, item in enumerate(QUIZ)]),
        html.Button("Conferir respostas", id='btn-quiz-check', n_clicks=0, style={
            'padding': '10px 20px', 'backgroundColor': C['primary'], 'color': 'white',
            'border': 'none', 'fontWeight': '600', 'cursor': 'pointer', 'fontSize': '0.9rem',
        }),
        html.Div(id='quiz-score', style={'marginTop': '14px', 'fontWeight': '700', 'color': C['primary']}),
    ], style=card())


def layout():
    return html.Div([
        html.H2("Módulo Educativo (SUS)", style={'color': C['primary'], 'margin': '0 0 6px'}),
        html.P(
            "Conteúdo de referência sobre o Sistema Único de Saúde, seus princípios, níveis de "
            "atenção e os direitos garantidos a quem o utiliza — complementar à análise de dados "
            "das demais abas.",
            style={'color': C['txt2'], 'marginBottom': '20px'},
        ),

        html.Div([
            _principio_card("Universalidade", "Saúde é direito de todos e dever do Estado — o "
                            "acesso ao SUS independe de renda, ocupação ou contribuição prévia.", C['primary']),
            _principio_card("Equidade", "Tratar desigualmente os desiguais: mais recursos e atenção "
                            "para quem tem maior necessidade, reduzindo diferenças de acesso.", C['secondary']),
            _principio_card("Integralidade", "O cuidado abrange promoção, prevenção, tratamento e "
                            "reabilitação, considerando a pessoa como um todo, não apenas a doença.", C['accent']),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '4px'}),

        html.Div([
            html.H3("Níveis de Atenção à Saúde", style={
                'color': C['primary'], 'marginTop': '0', 'borderBottom': f"1px solid {C['line']}",
                'paddingBottom': '10px', 'borderLeft': f"3px solid {C['accent']}", 'paddingLeft': '12px',
            }),
            html.Div([
                _nivel_card("Atenção Primária", ["UBS", "Equipe de Saúde da Família"],
                            "Porta de entrada preferencial do SUS: prevenção, cuidado contínuo e "
                            "coordenação do encaminhamento na rede.", C['primary']),
                _nivel_card("Atenção Secundária", ["Policlínicas", "Centros Especializados", "CAPS"],
                            "Consultas e exames especializados, geralmente acessados por "
                            "encaminhamento da atenção primária.", C['secondary']),
                _nivel_card("Atenção Terciária", ["Hospitais", "UPA", "SAMU"],
                            "Procedimentos de alta complexidade, internações e urgência/emergência.", C['danger']),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px'}),
        ], style=card()),

        _direitos(),
        _meu_sus_digital(),
        _quiz(),
    ], style={'padding': '20px 40px', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(app):
    @app.callback(
        Output({'type': 'quiz-feedback', 'index': ALL}, 'children'),
        Output('quiz-score', 'children'),
        Input('btn-quiz-check', 'n_clicks'),
        State({'type': 'quiz-opt', 'index': ALL}, 'value'),
        prevent_initial_call=True,
    )
    def check_quiz(n_clicks, respostas):
        feedbacks = []
        acertos = 0
        for item, resposta in zip(QUIZ, respostas):
            if resposta is None:
                feedbacks.append(html.Span("Selecione uma opção.", style={'color': C['txt2']}))
                continue
            certo = resposta == item['correta']
            acertos += int(certo)
            cor = C['secondary'] if certo else C['danger']
            tag = '✔ Correto' if certo else '✘ Incorreto'
            feedbacks.append(html.Div([
                html.Strong(tag, style={'color': cor}),
                html.Span(f" — {item['explicacao']}", style={'color': C['txt2']}),
            ]))
        score = f"Pontuação: {acertos} de {len(QUIZ)} corretas."
        return feedbacks, score
