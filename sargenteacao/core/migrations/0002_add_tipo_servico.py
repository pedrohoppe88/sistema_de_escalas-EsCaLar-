from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='servico',
            name='tipo',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('GUARDA', 'Guarda ao Quartel'),
                    ('PLANTAO', 'Plantão'),
                    ('PERMANENCIA', 'Permanência'),
                ],
                default='GUARDA',
            ),
        ),
    ]
