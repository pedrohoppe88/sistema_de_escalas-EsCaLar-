from datetime import date, timedelta
from .models import Militar, Afastamento, Servico


# 🔖 Status padronizados
STATUS_BAIXA = 'BAIXA'
STATUS_NORMAL = 'NORMAL'
STATUS_ALTA = 'ALTA'
STATUS_BLOQUEADO = 'BLOQUEADO'
STATUS_INAPTO = 'INAPTO'
STATUS_PRIMEIRO = 'PRIMEIRO SERVIÇO'
STATUS_JA_ESCALADO = 'JÁ ESCALADO'


def calcular_efetivo_por_data(data_referencia: date):
    hoje = data_referencia
    ontem = hoje - timedelta(days=1)

    resultado = []

    militares = Militar.objects.filter(ativo=True)

    for militar in militares:

        # 🔎 Já escalado hoje?
        ja_escalado = Servico.objects.filter(
            militar=militar,
            data=hoje
        ).exists()

        # 1️⃣ Verificar afastamento
        afastamento_ativo = Afastamento.objects.filter(
            militar=militar,
            data_inicio__lte=hoje,
            data_fim__gte=hoje
        ).first()

        if afastamento_ativo:
            resultado.append({
                'militar': militar,
                'apto': False,
                'motivo': afastamento_ativo.get_tipo_display(),
                'dias_folga': None,
                'status': STATUS_INAPTO,
                'ja_escalado': False
            })
            continue

        # 2️⃣ Último serviço
        ultimo_servico = Servico.objects.filter(
            militar=militar
        ).order_by('-data').first()

        if not ultimo_servico:
            dias_folga = None
        else:
            dias_folga = (hoje - ultimo_servico.data).days

            # ❌ Não pode tirar serviço em dias seguidos
            if ultimo_servico.data == ontem:
                resultado.append({
                    'militar': militar,
                    'apto': False,
                    'motivo': 'Serviço ontem',
                    'dias_folga': 0,
                    'status': STATUS_BLOQUEADO,
                    'ja_escalado': ja_escalado
                })
                continue

        # 3️⃣ Já escalado hoje (bloqueia)
        if ja_escalado:
            resultado.append({
                'militar': militar,
                'apto': False,
                'motivo': STATUS_JA_ESCALADO,
                'dias_folga': dias_folga,
                'status': STATUS_JA_ESCALADO,
                'ja_escalado': True
            })
            continue

        # 4️⃣ Definir status visual
        if dias_folga is None:
            status = STATUS_PRIMEIRO
        elif dias_folga <= 1:
            status = STATUS_BAIXA
        elif dias_folga <= 4:
            status = STATUS_NORMAL
        else:
            status = STATUS_ALTA

        resultado.append({
            'militar': militar,
            'apto': True,
            'motivo': 'Apto',
            'dias_folga': dias_folga,
            'status': status,
            'ja_escalado': False
        })

    # 🔽 Ordenação inteligente (mais justo)
    resultado = sorted(
        resultado,
        key=lambda x: (
            x['ja_escalado'],                          # escalados vão pro fim
            x['dias_folga'] if x['dias_folga'] is not None else 999
        ),
        reverse=True
    )

    return resultado


def calcular_efetivo_do_dia():
    return calcular_efetivo_por_data(date.today())
