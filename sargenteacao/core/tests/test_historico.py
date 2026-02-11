from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Militar, Servico


class HistoricoMilitarTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="admin", password="x")
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        self.militar = Militar.objects.create(nome="Teste", graduacao="SD", subunidade="Geral", ativo=True)
        hoje = date.today()
        Servico.objects.create(militar=self.militar, data=date(hoje.year, hoje.month, 1))
        Servico.objects.create(militar=self.militar, data=date(hoje.year, hoje.month, 2))
        prev_month = hoje.month - 1 if hoje.month > 1 else 12
        prev_year = hoje.year if hoje.month > 1 else hoje.year - 1
        Servico.objects.create(militar=self.militar, data=date(prev_year, prev_month, 28))

    def test_historico_context_and_pdf(self):
        hoje = date.today()
        url_hist = reverse("historico_militar", args=[self.militar.id])
        resp_hist = self.client.get(f"{url_hist}?mes={hoje.month}&ano={hoje.year}")
        self.assertEqual(resp_hist.status_code, 200)
        self.assertIn("total_mes", resp_hist.context)
        self.assertEqual(resp_hist.context["total_mes"], 2)
        url_pdf = reverse("relatorio_mensal_militar_pdf", args=[self.militar.id, hoje.year, hoje.month])
        resp_pdf = self.client.get(url_pdf)
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf["Content-Type"], "application/pdf")
        self.assertTrue(resp_pdf.content.startswith(b"%PDF"))
