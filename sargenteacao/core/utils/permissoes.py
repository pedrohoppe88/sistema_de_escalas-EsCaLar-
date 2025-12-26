def is_sargenteante(user):
    return user.groups.filter(name='SARGENTEANTE').exists()


def is_auxiliar(user):
    return user.groups.filter(name='AUXILIAR').exists()


def pode_registrar_servico(user):
    return is_sargenteante(user) or is_auxiliar(user)


def pode_gerar_pdf(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Sargenteante').exists()
    )
