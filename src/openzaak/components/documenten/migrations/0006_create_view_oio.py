from django.db import migrations

CREATE_OIO_VIEW = [
    """
    CREATE OR REPLACE VIEW documenten_objectinformatieobject AS
    SELECT uuid_generate_v5(b.uuid, 'besluit') AS UUID,
           b.informatieobject_id,
           'besluit' AS object_type,
           b.besluit_id,
           NULL AS zaak_id
    FROM besluiten_besluitinformatieobject b
    
    UNION ALL
    
    SELECT uuid_generate_v5(z.uuid, 'zaak') AS UUID,
           z.informatieobject_id,
           'zaak' AS object_type,
           NULL AS besluit_id,
           z.zaak_id
    FROM zaken_zaakinformatieobject z ;
    """
]


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0004_auto_20190820_0945"),
        ("besluiten", "0003_auto_20190820_0945"),
        ("documenten", "0005_install_uuid_extension"),
    ]

    operations = [migrations.RunSQL(CREATE_OIO_VIEW)]
