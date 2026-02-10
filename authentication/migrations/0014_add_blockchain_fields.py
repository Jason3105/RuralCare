# Generated migration for blockchain fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='qrcodescanlog',
            name='blockchain_tx_hash',
            field=models.CharField(blank=True, help_text='Ethereum transaction hash', max_length=66, null=True),
        ),
        migrations.AddField(
            model_name='qrcodescanlog',
            name='blockchain_log_id',
            field=models.BigIntegerField(blank=True, help_text='Smart contract log ID', null=True),
        ),
        migrations.AddField(
            model_name='qrcodescanlog',
            name='blockchain_block_number',
            field=models.BigIntegerField(blank=True, help_text='Block number on blockchain', null=True),
        ),
        migrations.AddField(
            model_name='qrcodescanlog',
            name='blockchain_verified',
            field=models.BooleanField(default=False, help_text='Whether logged on blockchain'),
        ),
    ]
