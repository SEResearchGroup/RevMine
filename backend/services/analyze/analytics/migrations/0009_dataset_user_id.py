from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0008_add_time_review_metrics_and_split_filetypes"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="user_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddIndex(
            model_name="dataset",
            index=models.Index(fields=["user_id"], name="datasets_user_id_f24d13_idx"),
        ),
    ]
