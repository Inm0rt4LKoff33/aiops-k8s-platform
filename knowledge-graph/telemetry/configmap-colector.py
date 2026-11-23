from datetime import datetime, timezone

from shared import core_v1, logging, json, event_watcher

logger = logging.getLogger(__name__)


def structure_configmap(tipo, obj):
    """Estructura un evento de ConfigMap en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    
    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "claves": json.dumps(list(obj.data.keys())) if obj.data else json.dumps([]),
        "inmutable": obj.immutable if obj.immutable is not None else False
    }

def insert_configmap(driver, params):
    """Inserta un ConfigMap en Neo4j."""
    with driver.session() as session:
        session.run("""
            MERGE (c:ConfigMap {uid: $uid})
            SET c.nombre = $nombre
            SET c.namespace = $namespace
            SET c.creado_en = $creado_en
            SET c.eliminado_en = $eliminado_en
            SET c.claves = $claves
            SET c.inmutable = $inmutable
        """, **params)

event_watcher(api_list=core_v1.list_namespaced_config_map,
              namespace="online-boutique",
              resource_version=None,
              structure_event=structure_configmap,
              insert_event=insert_configmap)