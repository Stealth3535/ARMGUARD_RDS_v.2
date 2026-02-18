from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0006_remove_transaction_print_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='transaction_mode',
            field=models.CharField(choices=[('normal', 'Normal Mode'), ('defcon', 'Defcon Mode')], default='normal', max_length=20),
        ),
    ]
