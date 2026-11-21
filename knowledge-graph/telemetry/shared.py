"""Configuración y clientes compartidos entre los colectores.

Cada colector importa de aquí lo que necesite (cliente de Kubernetes,
driver de Neo4j, constantes del proyecto) en vez de repetir su propia
inicialización.
"""
from datetime import datetime, timezone
import logging
import time
import json

from kubernetes.client.exceptions import ApiException
from kubernetes import client, config, watch

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)

config.load_kube_config()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "aiops-tfm-2026")
driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

logger = logging.getLogger(__name__)

ENTORNO_BY_NAMESPACE = {
    "online-boutique": "pruebas",
    "chaos-test": "pruebas",
}

def event_watcher(api_list=None, namespace=None, resource_version=None, structure_event=None, insert_event=None):
    """Devuelve un generador que produce eventos de Kubernetes.

    Cada evento es un diccionario con las claves 'type' y 'object'.
    """
    while(True):
        w = watch.Watch()
        try:
            for event in w.stream(api_list, 
                                namespace=namespace, 
                                resource_version=resource_version, 
                                timeout_seconds=30):

                tipo = event["type"]       # ADDED, MODIFIED, DELETED
                obj  = event["object"]     # el objeto Deployment completo

                resource_version = obj.metadata.resource_version  # Actualizamos el resource_version para la próxima llamada
                insert_event(driver, structure_event(tipo, obj))
                logger.info("Evento %s procesado para %s %s en namespace %s", tipo, type(obj).__name__, obj.metadata.name, obj.metadata.namespace)
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
            logger.warning("Connection error (%s), reconnecting in 5s", e)
            time.sleep(5)

        finally:
            w.stop()