from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_drf_filepond', '0005_add_uploaded_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storedupload',
            name='file_path',
            field=models.FileField(max_length=2048, upload_to=''),
        ),
        migrations.RenameField(
            model_name='storedupload',
            old_name='file_path',
            new_name='file'
        )
    ]
