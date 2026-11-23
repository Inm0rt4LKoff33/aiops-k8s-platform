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
networking_v1 = client.NetworkingV1Api()

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

def is_subset(subset_dict, superset_dict):
    """Devuelve True si subset_dict es un subconjunto de superset_dict."""
    return all(superset_dict.get(k) == v for k, v in subset_dict.items())

def get_candidates(session, namespace, label_node, flag : str):
    candidates = session.run(f"""
        MATCH (n:{label_node} {{namespace: $namespace}})
        WHERE n.eliminado_en IS NULL 
        AND n.{flag} IS NOT NULL
        RETURN n.uid AS uid, n.{flag} AS labels
    """, namespace=namespace)
    return list(candidates)

def get_matches(list_candidates, objective_label, first_match : bool, candidate_is_subset : bool):
    matches = []
    for candidate in list_candidates:
        candidate_labels = json.loads(candidate["labels"])

        candidate_matches = (is_subset(candidate_labels, objective_label) if candidate_is_subset 
                             else is_subset(objective_label, candidate_labels))
        if candidate_matches:
            if first_match:
                return candidate["uid"]
            else:    
                matches.append(candidate["uid"])
    return matches if matches else None
    