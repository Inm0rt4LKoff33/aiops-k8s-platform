from datetime import datetime, timezone

from shared import ENTORNO_BY_NAMESPACE,core_v1,logging, json, event_watcher

logger = logging.getLogger(__name__)

def structure_pod(tipo, obj):
    """Estructura un evento de Pod en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    labels = obj.metadata.labels  # Usamos las etiquetas del Pod como selector
    
    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "labels": json.dumps(labels)
    }

def insert_pod(driver, params):
    """Inserta un Pod en Neo4j."""
    with driver.session() as session:
        session.run("""
            MERGE (p:Pod {uid: $uid})
            SET p.nombre = $nombre
            SET p.namespace = $namespace
            SET p.creado_en = $creado_en
            SET p.eliminado_en = $eliminado_en
        """, **params)

        get_deployment_results = session.run("""
            MATCH (d:Deployment {namespace: $namespace})
            WHERE d.eliminado_en IS NULL AND d.selector IS NOT NULL
            RETURN d.uid AS uid, d.selector AS selector
        """, namespace=params["namespace"])

        matches = list(get_deployment_results)
        pod_labels = json.loads(params["labels"])
        if deployment_uid := compare_labels(matches, pod_labels):
            insert_relation_pod_deployment(session, {
                "uid": params["uid"],
                "namespace": params["namespace"],
                "deployment_uid": deployment_uid
            })

def compare_labels(matches, pod_labels):
    """Devuelve el uid del Deployment 
        cuyo selector es subconjunto de pod_labels, 
        o None si ninguno matchea."""
    
    for match in matches:
        selector_labels = json.loads(match["selector"])
        if all(pod_labels.get(k) == v for k, v in selector_labels.items()):
            return match["uid"]
    return None

def insert_relation_pod_deployment(session, params):
    """Inserta la relación entre un Pod y un Deployment en Neo4j."""
    
    session.run("""
        MATCH (p:Pod {uid: $uid})
        MATCH (d:Deployment {uid: $deployment_uid})
        WHERE d.eliminado_en IS NULL 
        AND d.selector IS NOT NULL
        AND d.namespace = $namespace
        MERGE (d)-[:GESTIONA]->(p)
    """, **params)

event_watcher(api_list=core_v1.list_namespaced_pod, 
              namespace="online-boutique", 
              resource_version=None, 
              structure_event=structure_pod, 
              insert_event=insert_pod)