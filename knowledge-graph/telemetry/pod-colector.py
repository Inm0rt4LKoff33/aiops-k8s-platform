from datetime import datetime, timezone

from shared import core_v1, get_candidates, get_matches, logging, json, event_watcher

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
            SET p.labels = $labels
        """, **params)

        get_deployment_candidates = get_candidates(session, params["namespace"], "Deployment", "selector")

        pod_labels = json.loads(params["labels"])
        if deployment_uid := get_matches(list(get_deployment_candidates), pod_labels, first_match=True, candidate_is_subset=True):
            insert_relation_pod_deployment(session, {
                "uid": params["uid"],
                "namespace": params["namespace"],
                "deployment_uid": deployment_uid
            })

        get_service_candidates = get_candidates(session, params["namespace"], "Service", "selector")
        if service_uid_list := get_matches(list(get_service_candidates), pod_labels, first_match=False, candidate_is_subset=True):
            for service_uid in service_uid_list:
                insert_relation_pod_service(session, {
                    "uid": service_uid,
                    "namespace": params["namespace"],
                    "pod_uid": params["uid"]
                })



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

def insert_relation_pod_service(session, params):
    """Inserta la relación entre un Service y un Pod en Neo4j."""
    
    session.run("""
        MATCH (s:Service {uid: $uid})
        MATCH (p:Pod {uid: $pod_uid})
        WHERE p.eliminado_en IS NULL 
        AND s.namespace = $namespace
        MERGE (s)-[:SELECCIONA]->(p)
    """, **params)

event_watcher(api_list=core_v1.list_namespaced_pod, 
              namespace="online-boutique", 
              resource_version=None, 
              structure_event=structure_pod, 
              insert_event=insert_pod)