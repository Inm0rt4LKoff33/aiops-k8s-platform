from shared_chaos import crd_watcher


def structure_experiment(tipo, obj):
  spec_delay = obj["spec"].get("delay")
  spec_stressors = obj["spec"].get("stressors")
  containers = obj.get("status", {}).get("experiment", {}).get("containerRecords", [])

  pods_inyectados = []

  for container in containers:
    splitted = container["id"].split("/")

    pods_inyectados.append({
      "namespace" : splitted[0],
      "nombre" : splitted[1],
      "container" : splitted[2] if len(splitted) > 2 else ""
    })

  return {
    "uid" : obj["metadata"]["uid"],
    "nombre" : obj["metadata"]["name"],
    "namespace" : obj["metadata"]["namespace"],
    "kind" : obj["kind"],
    "accion" : obj["spec"]["action"],
    "modo" : obj["spec"].get("mode"),
    "valor_modo" : obj["spec"].get("value"),
    "parametros" : [params for params in ([spec_delay, spec_stressors]) if params is not None],
    "duracion_seg" : obj["spec"]["duration"],
    "iniciado_en" : obj["metadata"]["creationTimestamp"],
    "finalizado_en" : None,
    "alerta_esperada" : obj["metadata"]["annotations"]["pruebas/alerta-esperada"].split(","),
    "deteccion_max_seg" : int(obj["metadata"]["annotations"]["pruebas/deteccion-max-seg"]),
    "containers" : containers,
    "pods_inyectados" : pods_inyectados
  }

def insert_experiment(driver, params):
  with driver.session() as session:
    session.run("""
        MERGE (ex:Experimento {uid: $uid})
        SET ex.uid = $uid
        SET ex.nombre = $nombre
        SET ex.namespace = $namespace
        SET ex.kind = $kind
        SET ex.accion = $accion
        SET ex.modo = $modo
        SET ex.valor_modo = $valor_modo
        SET ex.parametros = $parametros
        SET ex.duracion_seg = $duracion_seg
        SET ex.iniciado_en = datetime($iniciado_en)
        SET ex.finalizado_en = datetime($iniciado_en)
        SET ex.alerta_esperada = $alerta_esperada
        SET ex.deteccion_max_seg = $deteccion_max_seg
    """, **params)

    for pod_inyectado in params["pods_inyectados"]:
      insert_relation_experiment_pod(session, params={
        "uid" : params["uid"],
        "namespace" : pod_inyectado["namespace"],
        "nombre" : pod_inyectado["nombre"],
        "container" : pod_inyectado["container"]
      })

def insert_relation_experiment_pod(session, params):
   session.run("""
          MATCH (ex:Experimento {uid: $uid})
          MATCH (p:Pod {namespace: $namespace, nombre: $nombre})
          MERGE (ex)-[:INYECTADO_EN {container: $container}]->(p)
      """, **params)

crd_watcher(group="chaos-mesh.org", version="v1alpha1", 
            plural="podchaos", namespace="online-boutique",
            insert_event=insert_experiment, structure_event=structure_experiment)