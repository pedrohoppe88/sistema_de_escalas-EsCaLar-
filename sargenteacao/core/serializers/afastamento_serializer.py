from rest_framework import serializers
from ..models import Afastamento  # type: ignore

class AfastamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Afastamento
        fields = '__all__'

    def validate(self, data):
        militar = data['militar']
        data_inicio = data['data_inicio']
        data_fim = data['data_fim'] 

        # 1️⃣ Militar ativo
        if not militar.ativo:
            raise serializers.ValidationError(
                "Não é possível afastar um militar inativo."
            )

        # 2️⃣ Data final maior ou igual à inicial
        if data_fim < data_inicio:
            raise serializers.ValidationError(
                "A data final não pode ser anterior à data inicial."
            )

        # 3️⃣ Impedir afastamento sobreposto
        conflitos = Afastamento.objects.filter(
            militar=militar,
            data_inicio__lte=data_fim,
            data_fim__gte=data_inicio
        )

        # Se for edição, ignora ele mesmo
        if self.instance:
            conflitos = conflitos.exclude(id=self.instance.id)

        if conflitos.exists():
            raise serializers.ValidationError(
                "Já existe um afastamento nesse período."
            )

        return data
