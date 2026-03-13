# Generated migration to rename Cleaning table to CleanedData

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("collectors", "0003_create_cleaning"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Cleaning",
            new_name="CleanedData",
        ),
        migrations.AlterModelTable(
            name="cleaneddata",
            table="cleaned_data",
        ),
    ]
