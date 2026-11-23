from datetime import datetime, timezone

from shared import ENTORNO_BY_NAMESPACE,apps_v1,logging, json, event_watcher
import hashlib

logger = logging.getLogger(__name__)

def structure_deployment(tipo, obj):
    """Estructura un evento de Deployment en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    image = obj.spec.template.spec.containers[0].image
    strat_type = obj.spec.strategy.type
    selector = obj.spec.selector.match_labels  # Usamos el selector del Deployment

    # Calculos para extraer los valores necesarios para los ConfigMaps y Secrets asociados al Deployment
    configmap_volumes = get_configmap_volumes(obj)

    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "entorno": ENTORNO_BY_NAMESPACE.get(namespace, "desconocido"),
        "imagen": image,
        "estrategia": strat_type,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "selector" : json.dumps(selector),
        "configmap_volumes" : configmap_volumes
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

        if params["configmap_volumes"]:
            configset_uid = f'{params["uid"]}-configset'
            hash = build_hash_string(params)

            session.run("""
                MERGE (cs:ConfigSet {uid: $configset_uid})
                SET cs.description = $description
                SET cs.huella_spec = $huella
                WITH cs 
                MATCH (d:Deployment {uid: $uid})
                MERGE (d)-[:USA_CONFIG {huella_aplicada: $huella}]->(cs)
            """, configset_uid=configset_uid, huella=hash, description=f'Config. dedicado al {params["namespace"]}', uid=params["uid"])

            for volume in params["configmap_volumes"]:
                insert_relation_configset_configmap(session, {
                    "configset_uid": configset_uid,
                    "namespace": params["namespace"],
                    "orden": volume["orden"],
                    "modo" : "volumen",
                    "nombre_config_map": volume["nombre_config_map"],
                    "ruta": volume["path"]
                })

def insert_relation_configset_configmap(session, params):
    session.run("""
        MATCH (cs:ConfigSet {uid: $configset_uid})
        MATCH (cm:ConfigMap {nombre: $nombre_config_map, namespace: $namespace})
        MERGE (cs)-[:AGRUPA {orden: $orden, ruta: $ruta, modo: $modo}]->(cm)
    """, **params)

def get_configmap_volumes(obj):
    volumes_dict = []
    configmap_volumes = [volume for volume in (obj.spec.template.spec.volumes or []) if volume.config_map is not None]
    # secret_volumes = [volume.secret for volume in obj.spec.template.spec.volumes if volume.secret]

    container_volumes = obj.spec.template.spec.containers[0].volume_mounts

    for orden, configmap_volume in enumerate(configmap_volumes):
        for volume_mount in container_volumes:
            if configmap_volume.name == volume_mount.name:
                mount_paths = {
                    "orden" : orden,
                    "nombre_config_map" : configmap_volume.config_map.name,
                    "path": volume_mount.mount_path
                }
                volumes_dict.append(mount_paths)
            
    return volumes_dict

def build_hash_string(params):
    hashcoded = "".join(f"{v['nombre_config_map']}{v['path']}" for v in params["configmap_volumes"])
    hashstring_code = hashlib.sha256(hashcoded.encode()).hexdigest()
    return hashstring_code

event_watcher(api_list=apps_v1.list_namespaced_deployment, 
              namespace="online-boutique", 
              resource_version=None, 
              structure_event=structure_deployment, 
              insert_event=insert_deployment)