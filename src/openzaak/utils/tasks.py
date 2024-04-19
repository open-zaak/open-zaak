from openzaak import celery_app
from openzaak.utils.models import Import


# TODO: ensure one task is running all the time
@celery_app.task
def import_documents(import_pk: int) -> None:
    import_instance = Import.objects.get(pk=import_pk)  # noqa

    # TODO: validate metadata
    # TODO: save EIO's & read files
    raise NotImplementedError
