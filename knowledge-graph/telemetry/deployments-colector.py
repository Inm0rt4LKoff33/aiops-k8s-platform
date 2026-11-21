from datetime import datetime, timezone

from shared import ENTORNO_BY_NAMESPACE,apps_v1,logging, json, event_watcher

logger = logging.getLogger(__name__)

def structure_deployment(tipo, obj):
    """Estructura un evento de Deployment en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    image = obj.spec.template.spec.containers[0].image
    strat_type = obj.spec.strategy.type
    selector = obj.spec.selector.match_labels  # Usamos el selector del Deployment
    
    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "entorno": ENTORNO_BY_NAMESPACE.get(namespace, "desconocido"),
        "imagen": image,
        "estrategia": strat_type,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "selector" : json.dumps(selector)
    }

def insert_deployment(driver, params):
    """Inserta un Deployment en Neo4j."""
    with driver.session() as session:
        session.run("""
            MERGE (d:Deployment {uid: $uid})
            SET d.nombre = $nombre
            SET d.namespace = $namespace
            SET d.entorno = $entorno
            SET d.imagen = $imagen
            SET d.estrategia = $estrategia
            SET d.creado_en = $creado_en
            SET d.eliminado_en = $eliminado_en
            SET d.selector = $selector
        """, **params)

event_watcher(api_list=apps_v1.list_namespaced_deployment, 
              namespace="online-boutique", 
              resource_version=None, 
              structure_event=structure_deployment, 
              insert_event=insert_deployment)