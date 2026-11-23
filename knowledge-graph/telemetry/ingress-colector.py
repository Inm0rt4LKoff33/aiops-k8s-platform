from datetime import datetime, timezone

from shared import networking_v1, logging, json, event_watcher

logger = logging.getLogger(__name__)

def structure_ingress(tipo, obj):
    """Estructura un evento de Ingress en un diccionario listo para insertar en Neo4j."""
    uid = obj.metadata.uid
    namespace = obj.metadata.namespace
    creation_timestamp = obj.metadata.creation_timestamp
    rules = obj.spec.rules

    return {
        "uid": uid,
        "nombre": obj.metadata.name,
        "namespace": namespace,
        "creado_en": creation_timestamp,
        "eliminado_en": None if tipo != "DELETED" else datetime.now(timezone.utc),
        "rules": [rule.to_dict() for rule in rules] if rules else [], 
        "tls_habilitado": bool(obj.spec.tls)  # True si hay TLS configurado, False si no
    }

def insert_ingress(driver, params):
    """Inserta un Ingress en Neo4j."""
    with driver.session() as session:
      session.run("""
          MERGE (i:Ingress {uid: $uid})
          SET i.nombre = $nombre
          SET i.namespace = $namespace
          SET i.creado_en = $creado_en
          SET i.eliminado_en = $eliminado_en
          SET i.tls_habilitado = $tls_habilitado
      """, **params)

      rules_plain_dict = create_rules_dict(params["rules"])
      for rule in rules_plain_dict:
          rule_params = {
              "uid": params["uid"],
              "host": rule["host"],
              "path": rule["path"],
              "service_name": rule["service_name"],
              "namespace": params["namespace"]
          }
          insert_relation_ingress_service(session, rule_params)
      


def insert_relation_ingress_service(session, params):
    """Inserta la relación entre un Ingress y un Service en Neo4j."""
    
    session.run("""
        MATCH (i:Ingress {uid: $uid})
        MATCH (s:Service {nombre: $service_name, namespace: $namespace})
        MERGE (i)-[:ENRUTA_A {host: $host, path: $path}]->(s)
    """, **params)

def create_rules_dict(rules):
    """Crea un diccionario de reglas a partir de la lista de reglas del Ingress."""
    rules_dict = []

    for rule in rules:
        if "http" in rule and "paths" in rule["http"]:
          for path in rule["http"]["paths"]:
              path_dict = {
                  "host": rule.get("host", ""),
                  "path": path.get("path"),
                  "service_name": path.get("backend", {}).get("service", {}).get("name")
              }
              rules_dict.append(path_dict)

    return rules_dict

event_watcher(api_list=networking_v1.list_namespaced_ingress,
              namespace="online-boutique",
              resource_version=None,
              structure_event=structure_ingress,
              insert_event=insert_ingress)