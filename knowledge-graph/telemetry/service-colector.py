from datetime import datetime, timezone

from shared import core_v1, get_candidates, get_matches, logging, json, event_watcher

logger = logging.getLogger(__name__)

def structure_service(tipo, obj):
    """Estructura un evento de Service en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    selector = obj.spec.selector  # Usamos el selector del Service como selector
    
    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "tipo": obj.spec.type if obj.spec.type else None,
        "puerto": obj.spec.ports[0].port if obj.spec.ports else None,
        "target_port": obj.spec.ports[0].target_port if obj.spec.ports else None,
        "selector": json.dumps(selector) 
    }

def insert_service(driver, params):
    """Inserta un Service en Neo4j."""
    with driver.session() as session:
        session.run("""
            MERGE (s:Service {uid: $uid})
            SET s.nombre = $nombre
            SET s.namespace = $namespace
            SET s.creado_en = $creado_en
            SET s.eliminado_en = $eliminado_en
            SET s.tipo = $tipo
            SET s.puerto = $puerto
            SET s.target_port = $target_port
            SET s.selector = $selector
        """, **params)

        get_pods_candidates = get_candidates(session, params["namespace"], "Pod", "labels")

        pod_prematches = list(get_pods_candidates)
        service_labels = json.loads(params["selector"])
        if pod_uid_list := get_matches(pod_prematches, service_labels, first_match=False, candidate_is_subset=False):
            for pod_uid in pod_uid_list:
                insert_relation_service_pod(session, {
                    "uid": params["uid"],
                    "namespace": params["namespace"],
                    "pod_uid": pod_uid
                })

def insert_relation_service_pod(session, params):
    """Inserta la relación entre un Service y un Pod en Neo4j."""
    
    session.run("""
        MATCH (s:Service {uid: $uid})
        MATCH (p:Pod {uid: $pod_uid})
        WHERE p.eliminado_en IS NULL 
        AND s.namespace = $namespace
        MERGE (s)-[:SELECCIONA]->(p)
    """, **params)

event_watcher(api_list=core_v1.list_namespaced_service, 
              namespace="online-boutique", 
              resource_version=None, 
              structure_event=structure_service, 
              insert_event=insert_service)