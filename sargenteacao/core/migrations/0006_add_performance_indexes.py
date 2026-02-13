# Generated migration to add performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_servico_unique_special_role_per_day_and_more'),
    ]

    operations = [
        # Index for Servico.data - heavily used in date filtering
        migrations.AddIndex(
            model_name='servico',
            index=models.Index(fields=['data'], name='servico_data_idx'),
        ),
        
        # Composite index for Servico (data, militar) - common query pattern
        migrations.AddIndex(
            model_name='servico',
            index=models.Index(fields=['data', 'militar'], name='servico_data_mil_idx'),
        ),
        
        # Index for Afastamento.data_inicio - used in date range queries
        migrations.AddIndex(
            model_name='afastamento',
            index=models.Index(fields=['data_inicio'], name='afast_inicio_idx'),
        ),
        
        # Index for Afastamento.data_fim - used in date range queries
        migrations.AddIndex(
            model_name='afastamento',
            index=models.Index(fields=['data_fim'], name='afast_fim_idx'),
        ),
        
        # Composite index for Afastamento (data_inicio, data_fim) - common query pattern
        migrations.AddIndex(
            model_name='afastamento',
            index=models.Index(fields=['data_inicio', 'data_fim'], name='afast_periodo_idx'),
        ),
    ]
