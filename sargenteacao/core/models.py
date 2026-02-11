from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Militar(models.Model):
    GRADUACOES_CHOICES = [
        ('SD', 'Soldado'),
        ('CB', 'Cabo'),
        ('3SG', '3º Sargento'),
        ('2SG', '2º Sargento'),
        ('1SG', '1º Sargento'),
        ('ST', 'Subtenente'),
        ('ASP', 'Aspirante'),
        ('2TEN', '2º Tenente'),
        ('1TEN', '1º Tenente'),
        ('CAP', 'Capitão'),
        ('MAJ', 'Major'),
        ('TC', 'Tenente-Coronel'),
        ('CEL', 'Coronel'),
        ('GEN', 'General'),
    ]

    nome = models.CharField(max_length=100)
    graduacao = models.CharField(max_length=20, choices=GRADUACOES_CHOICES)
    subunidade = models.CharField(max_length=50)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} ({self.get_graduacao_display()})"


class Afastamento(models.Model):
    TIPOS_AFASTAMENTO = [
        ('FERIAS', 'Férias'),
        ('LICENCA', 'Licença'),
        ('DISPENSA', 'Dispensa'),
        ('MEDICA', 'Dispensa Médica'),
    ]

    militar = models.ForeignKey(
        Militar,
        on_delete=models.CASCADE,
        related_name='afastamentos'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_AFASTAMENTO
    )

    data_inicio = models.DateField()
    data_fim = models.DateField()

    observacoes = models.TextField(
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inicio']
        verbose_name = 'Afastamento'
        verbose_name_plural = 'Afastamentos'

    def __str__(self):
        return f'{self.militar.nome} - {self.tipo} ({self.data_inicio} a {self.data_fim})'


class Servico(models.Model):
    TIPOS_SERVICO = [
        ('GUARDA', 'Guarda ao Quartel'),
        ('PLANTAO', 'Plantão'),
        ('PERMANENCIA', 'Permanência'),
        ('COMANDANTE_GUARDA', 'Comandante da Guarda'),
        ('CABO_GUARDA', 'Cabo da Guarda'),
        ('CABO_DIA', 'Cabo de Dia'),
        ('ADJUNTO', 'Adjunto'),
        ('OFICIAL_DIA', 'Oficial de Dia'),
    ]
    militar = models.ForeignKey(
        Militar,
        on_delete=models.CASCADE,
        related_name='servicos'
    )

    data = models.DateField()

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_SERVICO,
        default='GUARDA'
    )

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('militar', 'data')
        constraints = [
            models.UniqueConstraint(
                fields=['data', 'tipo'],
                condition=Q(tipo__in=['OFICIAL_DIA', 'ADJUNTO', 'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA']),
                name='unique_special_role_per_day',
            )
        ]
        ordering = ['-data']
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'

    def clean(self):
        # Não permitir serviço durante afastamento
        afastado = Afastamento.objects.filter(
            militar=self.militar,
            data_inicio__lte=self.data,
            data_fim__gte=self.data
        ).exists()

        if afastado:
            raise ValidationError(
                'Não é possível registrar serviço para militar afastado.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.militar.nome} - {self.get_tipo_display()} - {self.data.strftime('%d/%m/%Y')}"
