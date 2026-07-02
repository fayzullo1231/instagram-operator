from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.CharField(blank=True, db_index=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="product",
            name="keywords",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
