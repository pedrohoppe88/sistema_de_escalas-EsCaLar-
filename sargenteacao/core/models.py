from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Militar(models.Model):
    nome = models.CharField(max_length=100)
    graduacao = models.CharField(max_length=20)
    subunidade = models.CharField(max_length=50)
    ativo = models.BooleanField(default=True)
    
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
    
    tipo = models.CharField(max_length=20, choices=TIPOS_AFASTAMENTO)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    observacoes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.militar.nome} - {self.tipo})"
    
class Servico(models.Model):
    militar = models.ForeignKey(
        'Militar',
        on_delete=models.CASCADE,
        related_name='servicos'
    )

    data = models.DateField()

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('militar', 'data')
        ordering = ['-data']
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'

    def __str__(self):
        return f"{self.militar.nome} - {self.data.strftime('%d/%m/%Y')}"
    

    