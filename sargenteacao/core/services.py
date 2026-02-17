from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q, Sum, Case, When, IntegerField

from .models import Militar, Afastamento, Servico


# ==================== CONFIGURAÇÃO DE CACHE ====================

# Tempo de cache em segundos (5 minutos)
CACHE_TIMEOUT_EFETIVO = 300

# Prefixo para as chaves de cache
CACHE_PREFIX_EFETIVO = 'efetivo_'


# ==================== FUNÇÕES AUXILIARES DE CACHE ====================

def gerar_chave_cache_efetivo(data: date) -> str:
    """
    Gera uma chave de cache para o efetivo de uma data específica.
    
    Args:
        data: Data para a qual gerar a chave de cache
        
    Returns:
        String com a chave de cache formatada
    """
    return f"{CACHE_PREFIX_EFETIVO}{data.isoformat()}"


def invalidar_cache_efetivo(data: date) -> None:
    """
    Invalida o cache do efetivo para uma data específica.
    
    Args:
        data: Data para a qual invalidar o cache
    """
    chave = gerar_chave_cache_efetivo(data)
    cache.delete(chave)


# 🔖 Status padronizados
STATUS_BAIXA = 'BAIXA'
STATUS_NORMAL = 'NORMAL'
STATUS_ALTA = 'ALTA'
STATUS_BLOQUEADO = 'BLOQUEADO'
STATUS_INAPTO = 'INAPTO'
STATUS_PRIMEIRO = 'PRIMEIRO SERVIÇO'
STATUS_JA_ESCALADO = 'JÁ ESCALADO'

# Cargos especiais que devem ser únicos por dia
CARGOS_ESPECIAIS = {'OFICIAL_DIA', 'ADJUNTO', 'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA'}

# Mapeamento de tipos de serviço para labels
TIPO_SERVICO_LABELS = dict(Servico.TIPOS_SERVICO)

# Seções do aditamento em ordem
ADITAMENTO_SECTIONS = [
    ('COMANDANTE_GUARDA', 'Comandante da Guarda'),
    ('CABO_GUARDA', 'Cabo da Guarda'),
    ('CABO_DIA', 'Cabo de Dia'),
    ('ADJUNTO', 'Adjunto'),
    ('OFICIAL_DIA', 'Oficial de Dia'),
    ('GUARDA', 'Guarda ao Quartel'),
    ('PLANTAO', 'Plantão'),
    ('PERMANENCIA', 'Permanência'),
]


# ==================== REGRAS DE NEGÓCIO ====================

def tipos_permitidos_por_graduacao(grad: str) -> List[str]:
    """
    Retorna a lista de tipos de serviço permitidos para uma determinada graduação.
    
    Args:
        grad: A graduação militar (SD, CB, 3SG, etc.)
        
    Returns:
        Lista de códigos de tipo de serviço permitidos
    """
    base = ['GUARDA', 'PLANTAO', 'PERMANENCIA']
    allowed = []
    
    if grad in ('SD', 'CB'):
        allowed.extend(base)
    if grad == 'CB':
        allowed.extend(['CABO_GUARDA', 'CABO_DIA'])
    if grad == '3SG':
        allowed.append('COMANDANTE_GUARDA')
    if grad in ('2SG', '1SG'):
        allowed.append('ADJUNTO')
    if grad in ('1TEN', '2TEN'):
        allowed.append('OFICIAL_DIA')
    
    return allowed


def graduacoes_permitidas_por_tipo(tipo: str) -> List[str]:
    """
    Retorna a lista de graduações permitidas para um determinado tipo de serviço.
    Esta é a função inversa de tipos_permitidos_por_graduacao.
    
    Args:
        tipo: O código do tipo de serviço (GUARDA, CABO_GUARDA, etc.)
        
    Returns:
        Lista de códigos de graduação permitidos
    """
    # GUARDA, PLANTAO, PERMANENCIA podem ser feitos por todas as graduações
    if tipo in ('GUARDA', 'PLANTAO', 'PERMANENCIA'):
        return ['SD', 'CB', '3SG', '2SG', '1SG', '1TEN', '2TEN']
    
    # CABO_GUARDA e CABO_DIA só podem ser feitos por CB
    if tipo in ('CABO_GUARDA', 'CABO_DIA'):
        return ['CB']
    
    # COMANDANTE_GUARDA só pode ser feito por 3SG
    if tipo == 'COMANDANTE_GUARDA':
        return ['3SG']
    
    # ADJUNTO pode ser feito por 2SG ou 1SG
    if tipo == 'ADJUNTO':
        return ['2SG', '1SG']
    
    # OFICIAL_DIA pode ser feito por 1TEN ou 2TEN
    if tipo == 'OFICIAL_DIA':
        return ['1TEN', '2TEN']
    
    return []


def get_opcoes_tipo_por_militar(militar: Militar) -> List[tuple]:
    """
    Retorna as opções de tipo de serviço para um militar específico.
    
    Args:
        militar: Instância do Militar
        
    Returns:
        Lista de tuplas (código, label) com os tipos permitidos
    """
    grad = militar.graduacao
    allowed_codes = tipos_permitidos_por_graduacao(grad)
    return [(code, TIPO_SERVICO_LABELS[code]) for code in allowed_codes]


def get_tipos_ocupados_por_data(data: date) -> List[str]:
    """
    Retorna a lista de tipos de serviço especiais já ocupados para uma data.
    
    Args:
        data: Data de referência
        
    Returns:
        Lista de códigos de tipo já ocupados
    """
    return list(
        Servico.objects.filter(data=data, tipo__in=CARGOS_ESPECIAIS)
        .values_list('tipo', flat=True)
    )


# ==================== CÁLCULO DE EFETIVO ====================

def calcular_efetivo_por_data(data_referencia: date):
    """
    Calcula o efetivo para uma data específica.
    
    OTIMIZADO: Usa cache para evitar queries repetidas.
    O resultado é armazenado em cache por 5 minutos.
    
    Args:
        data_referencia: Data para calcular o efetivo
        
    Returns:
        Lista de dicionários com informações do militar e seu status
    """
    # 🔍 Verificar se o resultado já está em cache
    chave_cache = gerar_chave_cache_efetivo(data_referencia)
    resultado_cache = cache.get(chave_cache)
    
    if resultado_cache is not None:
        return resultado_cache
    
    # Se não está em cache, calcular o efetivo
    hoje = data_referencia
    ontem = hoje - timedelta(days=1)

    # ========== OTIMIZAÇÃO: Buscar todos os dados de uma vez ==========
    
    # 1️⃣ Buscar TODOS os militares ativos de uma vez
    militares = Militar.objects.filter(ativo=True)
    militares_list = list(militares)
    militar_ids = [m.id for m in militares_list]
    
    if not militares_list:
        cache.set(chave_cache, [], CACHE_TIMEOUT_EFETIVO)
        return []
    
    # 2️⃣ Buscar TODOS os serviços de HOJE de uma vez (para todos os militares)
    servicos_hoje = set(
        Servico.objects.filter(data=hoje, militar_id__in=militar_ids)
        .values_list('militar_id', flat=True)
    )
    
    # 3️⃣ Buscar TODOS os afastamentos ATIVOS de uma vez
    afastamentos_hoje = Afastamento.objects.filter(
        data_inicio__lte=hoje,
        data_fim__gte=hoje,
        militar_id__in=militar_ids
    ).select_related('militar')
    
    # Criar dict: {militar_id: afastamento}
    afastamentos_dict = {a.militar_id: a for a in afastamentos_hoje}
    
    # 4️⃣ Buscar o ÚLTIMO serviço de CADA militar de uma vez
    # Usamos uma subconsulta para pegar apenas o último serviço por militar
    from django.db.models import Max
    
    # Pegar IDs dos últimos serviços
    ultimo_servico_ids = (
        Servico.objects.filter(militar_id__in=militar_ids)
        .values('militar_id')
        .annotate(max_data=Max('data'))
    )
    
    # Agora buscar os serviços completos desses IDs
    ultimo_servico_data = {}
    if ultimo_servico_ids.exists():
        # Criar um dicionário {militar_id: data_do_ultimo_servico}
        for item in ultimo_servico_ids:
            ultimo_servico_data[item['militar_id']] = item['max_data']
    
    # Se precisamos dos objetos Servico completos (para algo além da data),
    # buscaríamos aqui. Mas como só precisamos da data, o dict acima é suficiente.
    
    # ========== Processar dados em memória ==========
    resultado = []
    
    for militar in militares_list:
        militar_id = militar.id
        
        # 🔎 Já escalado hoje? (agora é O(1) com set)
        ja_escalado = militar_id in servicos_hoje
        
        # 1️⃣ Verificar afastamento (agora é O(1) com dict)
        afastamento_ativo = afastamentos_dict.get(militar_id)
        
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

        # 2️⃣ Último serviço (agora é O(1) com dict)
        ultima_data = ultimo_servico_data.get(militar_id)
        
        if not ultima_data:
            dias_folga = None
        else:
            dias_folga = (hoje - ultima_data).days

            # ❌ Não pode tirar serviço em dias seguidos (regra de negócio)
            if ultima_data == ontem:
                resultado.append({
                    'militar': militar,
                    'apto': False,
                    'motivo': 'Serviço ontem',
                    'dias_folga': 0,
                    'status': STATUS_BAIXA,
                    'ja_escalado': False
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

    # 💾 Armazenar o resultado em cache
    cache.set(chave_cache, resultado, CACHE_TIMEOUT_EFETIVO)
    
    return resultado


def calcular_efetivo_do_dia():
    """Calcula o efetivo para o dia de hoje."""
    return calcular_efetivo_por_data(date.today())


# ==================== SERVIÇOS ====================

def filtrar_militares_aptos(efetivo: List[Dict], query: str = '', graduacao: str = '') -> List[Dict]:
    """
    Filtra militares aptos com base em query de busca e graduação.
    
    Args:
        efetivo: Lista de efetivo calculada
        query: Texto para busca no nome
        graduacao: Graduação para filtro
        
    Returns:
        Lista filtrada de militares aptos
    """
    militares_aptos = []
    for e in efetivo:
        if e['apto']:
            if query and query.lower() not in e['militar'].nome.lower():
                continue
            if graduacao and e['militar'].graduacao != graduacao:
                continue
            grad = e['militar'].graduacao
            allowed_codes = tipos_permitidos_por_graduacao(grad)
            e['opcoes_tipo'] = [(code, TIPO_SERVICO_LABELS[code]) for code in allowed_codes]
            militares_aptos.append(e)
    return militares_aptos


def filtrar_militares_nao_aptos(efetivo: List[Dict], query: str = '', graduacao: str = '') -> List[Dict]:
    """
    Filtra militares não aptos com base em query de busca e graduação.
    """
    return [
        e for e in efetivo
        if not e['apto']
        and (not query or query.lower() in e['militar'].nome.lower())
        and (not graduacao or e['militar'].graduacao == graduacao)
    ]


def pode_atribuir_tipo(militar: Militar, tipo: str, data: date, servico_id: int = None) -> tuple:
    """
    Verifica se um tipo de serviço pode ser atribuído a um militar.
    
    Args:
        militar: Instância do Militar
        tipo: Código do tipo de serviço
        data: Data do serviço
        servico_id: ID do serviço sendo editado (para exclusão na validação)
        
    Returns:
        Tupla (bool, str) - (pode_atribuir, mensagem_erro)
    """
    # Verifica se o tipo é permitido para a graduação
    allowed_codes = tipos_permitidos_por_graduacao(militar.graduacao)
    if tipo not in allowed_codes:
        return False, 'Tipo de serviço não permitido para a graduação selecionada.'
    
    # Verifica se o militar já tem serviço nesta data
    query = Servico.objects.filter(militar=militar, data=data)
    if servico_id:
        query = query.exclude(id=servico_id)
    if query.exists():
        return False, 'Militar já possui serviço na data.'
    
    # Verifica se é cargo especial único
    if tipo in CARGOS_ESPECIAIS:
        query = Servico.objects.filter(data=data, tipo=tipo)
        if servico_id:
            query = query.exclude(id=servico_id)
        if query.exists():
            return False, f'Tipo {tipo.replace("_", " ").title()} já atribuído para a data selecionada.'
    
    return True, ''


def registrar_servicos(militares_selecionados: List[Militar], tipos: Dict[int, str], 
                       data: date, registrado_por: User) -> Dict[str, Any]:
    """
    Registra serviços para militares selecionados.
    
    Args:
        militares_selecionados: Lista de objetos Militar
        tipos: Dicionário {militar_id: tipo_servico}
        data: Data do serviço
        registrado_por: Usuário que está registrando
        
    Returns:
        Dicionário com estatísticas do registro
    """
    registrados = 0
    ignorados = 0
    erros = []
    
    for militar in militares_selecionados:
        tipo = tipos.get(militar.id, 'GUARDA')
        
        # Validações
        pode_atribuir, erro = pode_atribuir_tipo(militar, tipo, data)
        if not pode_atribuir:
            erros.append(f'{militar.nome}: {erro}')
            continue
        
        try:
            Servico.objects.create(
                militar=militar,
                data=data,
                tipo=tipo,
                registrado_por=registrado_por
            )
            registrados += 1
        except Exception as e:
            erros.append(f'{militar.nome}: {str(e)}')
            ignorados += 1
    
    return {
        'registrados': registrados,
        'ignorados': ignorados,
        'erros': erros
    }


def atualizar_servico(servico: Servico, novo_militar: Militar, novo_tipo: str, 
                     atualizado_por: User, data: date) -> tuple:
    """
    Atualiza um serviço existente.
    
    Args:
        servico: Instância do Servico a ser atualizado
        novo_militar: Novo militar atribuído
        novo_tipo: Novo tipo de serviço
        atualizado_por: Usuário que está atualizando
        data: Data do serviço
        
    Returns:
        Tupla (bool, str) - (sucesso, mensagem)
    """
    pode_atribuir, erro = pode_atribuir_tipo(novo_militar, novo_tipo, data, servico.id)
    if not pode_atribuir:
        return False, erro
    
    servico.militar = novo_militar
    servico.tipo = novo_tipo
    servico.registrado_por = atualizado_por
    servico.save()
    
    return True, 'Serviço atualizado com sucesso.'


def excluir_servico(servico: Servico) -> bool:
    """
    Exclui um serviço.
    
    Args:
        servico: Instância do Servico a ser excluído
        
    Returns:
        True se excluiu com sucesso
    """
    servico.delete()
    return True


def adicionar_servico(militar: Militar, tipo: str, data: date, registrado_por: User) -> tuple:
    """
    Adiciona um novo serviço.
    
    Args:
        militar: Militar a ser escalado
        tipo: Tipo de serviço
        data: Data do serviço
        registrado_por: Usuário que está registrando
        
    Returns:
        Tupla (bool, str) - (sucesso, mensagem)
    """
    pode_atribuir, erro = pode_atribuir_tipo(militar, tipo, data)
    if not pode_atribuir:
        return False, erro
    
    Servico.objects.create(
        militar=militar,
        data=data,
        tipo=tipo,
        registrado_por=registrado_por
    )
    
    return True, 'Serviço adicionado com sucesso.'


# ==================== ESTATÍSTICAS ====================

def calcular_estatisticas_servico(inicio: date, fim: date, 
                                  nome: str = '', graduacao: str = '', 
                                  subunidade: str = '') -> List[Dict]:
    """
    Calcula estatísticas de serviços para um período.
    
    Args:
        inicio: Data inicial
        fim: Data final
        nome: Filtro por nome
        graduacao: Filtro por graduação
        subunidade: Filtro por subunidade
        
    Returns:
        Lista de dicionários com estatísticas por militar
    """
    servicos_qs = Servico.objects.filter(data__gte=inicio, data__lte=fim).select_related('militar')
    
    if nome:
        servicos_qs = servicos_qs.filter(militar__nome__icontains=nome)
    if graduacao:
        servicos_qs = servicos_qs.filter(militar__graduacao=graduacao)
    if subunidade:
        servicos_qs = servicos_qs.filter(militar__subunidade=subunidade)

    stats_qs = servicos_qs.values('militar_id').annotate(
        total=Count('id'),
        guarda=Sum(Case(When(tipo='GUARDA', then=1), default=0, output_field=IntegerField())),
        plantao=Sum(Case(When(tipo='PLANTAO', then=1), default=0, output_field=IntegerField())),
        permanencia=Sum(Case(When(tipo='PERMANENCIA', then=1), default=0, output_field=IntegerField())),
        comandante_guarda=Sum(Case(When(tipo='COMANDANTE_GUARDA', then=1), default=0, output_field=IntegerField())),
        cabo_guarda=Sum(Case(When(tipo='CABO_GUARDA', then=1), default=0, output_field=IntegerField())),
        cabo_dia=Sum(Case(When(tipo='CABO_DIA', then=1), default=0, output_field=IntegerField())),
        adjunto=Sum(Case(When(tipo='ADJUNTO', then=1), default=0, output_field=IntegerField())),
        oficial_dia=Sum(Case(When(tipo='OFICIAL_DIA', then=1), default=0, output_field=IntegerField())),
    )

    militar_ids = [row['militar_id'] for row in stats_qs]
    militares_map = {m.id: m for m in Militar.objects.filter(id__in=militar_ids)}

    stats = []
    for row in stats_qs:
        m = militares_map.get(row['militar_id'])
        if not m:
            continue
        stats.append({
            'militar': m,
            'graduacao': m.get_graduacao_display(),
            'subunidade': m.subunidade,
            'total': row['total'],
            'guarda': row['guarda'],
            'plantao': row['plantao'],
            'permanencia': row['permanencia'],
            'comandante_guarda': row['comandante_guarda'],
            'cabo_guarda': row['cabo_guarda'],
            'cabo_dia': row['cabo_dia'],
            'adjunto': row['adjunto'],
            'oficial_dia': row['oficial_dia'],
        })

    return sorted(stats, key=lambda x: x['total'], reverse=True)


def calcular_contagem_por_tipo(servicos_qs) -> Dict[str, int]:
    """
    Calcula a contagem de serviços por tipo.
    
    Args:
        servicos_qs: QuerySet de serviços
        
    Returns:
        Dicionário com contagem por tipo
    """
    tipos_order = [
        'GUARDA', 'PLANTAO', 'PERMANENCIA',
        'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA',
        'ADJUNTO', 'OFICIAL_DIA'
    ]
    tipo_agg = servicos_qs.values('tipo').annotate(count=Count('id'))
    tipo_count_map = {row['tipo']: row['count'] for row in tipo_agg}
    
    return {
        'labels': [TIPO_SERVICO_LABELS[t] for t in tipos_order],
        'values': [tipo_count_map.get(t, 0) for t in tipos_order]
    }


# ==================== CALENDÁRIO ====================

# Cores para tipos de serviço no calendário
TIPO_COLORS = {
    'COMANDANTE_GUARDA': '#795548',
    'CABO_GUARDA': '#8D6E63',
    'CABO_DIA': '#9C27B0',
    'ADJUNTO': '#3F51B5',
    'OFICIAL_DIA': '#3949AB',
    'GUARDA': '#009688',
    'PLANTAO': '#2196F3',
    'PERMANENCIA': '#607D8B',
    'AFASTAMENTO': '#E53935',
}


def gerar_eventos_calendario(start: date, end: date, subunidade: str = None) -> List[Dict]:
    """
    Gera eventos para o calendário.
    
    Args:
        start: Data inicial
        end: Data final
        subunidade: Filtro por subunidade
        
    Returns:
        Lista de eventos no formato do FullCalendar
    """
    qs_serv = Servico.objects.filter(data__gte=start, data__lte=end).select_related('militar')
    qs_afast = Afastamento.objects.filter(data_inicio__lte=end, data_fim__gte=start).select_related('militar')
    
    if subunidade:
        qs_serv = qs_serv.filter(militar__subunidade=subunidade)
        qs_afast = qs_afast.filter(militar__subunidade=subunidade)
    
    events = []
    
    # Eventos de serviços
    for s in qs_serv:
        events.append({
            'id': f'srv-{s.id}',
            'title': s.militar.nome,
            'start': s.data.isoformat(),
            'end': (s.data + timedelta(days=1)).isoformat(),
            'allDay': True,
            'color': TIPO_COLORS.get(s.tipo, '#1976D2'),
            'extendedProps': {
                'tipo': s.tipo,
                'militarId': s.militar.id,
            }
        })
    
    # Eventos de afastamentos
    for a in qs_afast:
        events.append({
            'id': f'af-{a.id}',
            'title': a.militar.nome,
            'start': a.data_inicio.isoformat(),
            'end': (a.data_fim + timedelta(days=1)).isoformat(),
            'allDay': True,
            'color': TIPO_COLORS['AFASTAMENTO'],
            'extendedProps': {
                'tipo': 'AFASTAMENTO',
                'militarId': a.militar.id,
            }
        })
    
    return events


# ==================== HISTÓRICO ====================

def get_historico_servicos(militar: Militar, ano: int = None, mes: int = None):
    """
    Obtém o histórico de serviços de um militar.
    
    Args:
        militar: Instância do Militar
        ano: Ano para filtro (opcional)
        mes: Mês para filtro (opcional)
        
    Returns:
        QuerySet de serviços ordenados por data
    """
    servicos = Servico.objects.filter(militar=militar).order_by('-data')
    
    if ano:
        servicos = servicos.filter(data__year=ano)
    if mes:
        servicos = servicos.filter(data__month=mes)
    
    return servicos


def get_estatisticas_historico(militar: Militar, ano: int, mes: int) -> Dict:
    """
    Obtém estatísticas do histórico de um militar.
    
    Args:
        militar: Instância do Militar
        ano: Ano de referência
        mes: Mês de referência
        
    Returns:
        Dicionário com estatísticas
    """
    servicos = Servico.objects.filter(militar=militar)
    
    total_servicos = servicos.count()
    ultimo_servico = servicos.order_by('-data').first()
    total_mes = servicos.filter(data__month=mes, data__year=ano).count()
    
    return {
        'total_servicos': total_servicos,
        'ultimo_servico': ultimo_servico,
        'total_mes': total_mes
    }
