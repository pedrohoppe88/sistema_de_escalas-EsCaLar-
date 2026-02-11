from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Militar, Servico


class UnicidadeCargosEspeciaisTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="admin", password="x")
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.m1 = Militar.objects.create(nome="Militar 1", graduacao="1TEN", subunidade="Geral", ativo=True)
        self.m2 = Militar.objects.create(nome="Militar 2", graduacao="2SG", subunidade="Geral", ativo=True)
        self.hoje = date.today()

    def test_unico_oficial_dia_por_data(self):
        Servico.objects.create(militar=self.m1, data=self.hoje, tipo='OFICIAL_DIA', registrado_por=self.user)
        with self.assertRaises(Exception):
            Servico.objects.create(militar=self.m2, data=self.hoje, tipo='OFICIAL_DIA', registrado_por=self.user)

    def test_unico_adjunto_por_data(self):
        Servico.objects.create(militar=self.m2, data=self.hoje, tipo='ADJUNTO', registrado_por=self.user)
        with self.assertRaises(Exception):
            Servico.objects.create(militar=self.m1, data=self.hoje, tipo='ADJUNTO', registrado_por=self.user)
