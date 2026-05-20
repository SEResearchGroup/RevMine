from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0009_dataset_user_id"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="dataset",
            name="datasets_user_id_f24d13_idx",
        ),
    ]
