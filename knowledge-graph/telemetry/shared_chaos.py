import time

from kubernetes.client import ApiException

from shared import driver, logging, client, watch

custom_objects_api = client.CustomObjectsApi()
logger = logging.getLogger(__name__)


def crd_watcher(group=None, version=None, plural=None, 
                 namespace=None, resource_version=None, 
                 structure_event=None, insert_event=None):
  while(True):
    crd_w = watch.Watch()

    try:
      for event in crd_w.stream(custom_objects_api.list_namespaced_custom_object, 
                              group=group,
                              version=version,
                              plural=plural,
                              namespace=namespace,
                              resource_version=resource_version,
                              timeout_seconds=30):
        tipo = event["type"]
        obj = event["object"]
        resource_version = obj["metadata"]["resourceVersion"]  # Actualizamos el resource_version para la próxima llamada
        insert_event(driver, structure_event(tipo, obj))
        logger.info("Evento %s procesado para %s %s en namespace %s", tipo, type(obj).__name__, obj["metadata"]["name"], obj["metadata"]["namespace"])
    except ApiException as e:
      if e.status == 410:
          # resource_version expired — re-list to get a fresh one
          logger.warning("410 Gone, re-listing to refresh resource_version")
          resource_version = None
      else:
          logger.error("ApiException %s, retrying in 5s", e.status)
          time.sleep(5)
    except Exception as e:
          # ProtocolError, ConnectionError, etc.
          logger.exception("Exception error : ", e)
          time.sleep(5)
    finally:
      crd_w.stop()