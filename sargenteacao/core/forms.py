"""
Formulários Django para o sistema de sargenteação.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Militar


class LoginForm(forms.Form):
    """Formulário de login."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome de usuário',
            'type': 'text',
            'inputmode': 'text',
            'autocomplete': 'username',
            'style': 'background-image: none !important;'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha'
        })
    )


class RegistrationForm(UserCreationForm):
    """Formulário de registro de novos usuários/militares."""
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    graduacao = forms.ChoiceField(
        choices=Militar.GRADUACOES_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = UserCreationForm.Meta.model
        fields = ('username', 'email', 'graduacao', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome de usuário'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Senha'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirmar senha'
            }),
        }


class MilitarForm(forms.ModelForm):
    """Formulário para criação e edição de militares."""
    
    class Meta:
        model = Militar
        fields = ['nome', 'graduacao', 'subunidade', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),
            'graduacao': forms.Select(attrs={
                'class': 'form-control'
            }, choices=Militar.GRADUACOES_CHOICES),
            'subunidade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subunidade'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class AfastamentoForm(forms.ModelForm):
    """Formulário para criação e edição de afastamentos."""
    
    class Meta:
        from .models import Afastamento
        model = Afastamento
        fields = ['militar', 'tipo', 'data_inicio', 'data_fim', 'observacoes']
        widgets = {
            'militar': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
