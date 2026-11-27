# Manual de operación — AIOps Kubernetes Platform

Guía práctica de comandos para levantar, probar y explorar la plataforma.
No es documentación de arquitectura (eso está en `infra/README.md` y en el
TFM) — es el manual de "cómo lo prendo y cómo pruebo que funciona".

## 1. Antes de empezar

Verifica que el clúster esté sano (el control-plane de `kind` a veces se
reinicia solo):

```bash
kubectl get nodes
```

Si no responde o da error `Forbidden`, espera unos segundos y reintenta.

Si vas a consultar Neo4j desde tu máquina (Neo4j Browser o scripts propios),
necesitas el túnel hacia el clúster — en dos terminales separadas:

```bash
kubectl port-forward -n knowledge-graph svc/neo4j 7687:7687
```

```bash
kubectl port-forward -n knowledge-graph svc/neo4j 7474:7474
```

El primero es el protocolo Bolt (lo usan los scripts de Python). El segundo
es la interfaz web — ábrela en `http://localhost:7474`, conéctate con
`bolt://localhost:7687`, usuario `neo4j`, contraseña `aiops-tfm-2026`.

**Importante:** si vas a correr uno de estos comandos y el puerto ya está
ocupado por un `port-forward` que dejaste corriendo de una sesión anterior,
mátalo primero (`pkill -f "port-forward.*7687"`) o vas a tener dos procesos
compitiendo por el mismo puerto.

## 2. Levantar los colectores

### Opción A — con el orquestador (recomendado)

```bash
cd pipeline
python orchestrator.py
```

Levanta los siete colectores de una vez (los cinco de topología más los dos
tipos de experimento de caos), los supervisa, y reinicia automáticamente
cualquiera que se caiga. `Ctrl+C` los apaga todos limpiamente.

### Opción B — manual, uno por uno (para depurar un colector específico)

Cada uno en su propia terminal, desde `knowledge-graph/telemetry/`:

```bash
cd knowledge-graph/telemetry
uv run pod-colector.py
```

```bash
uv run service-colector.py
```

```bash
uv run ingress-colector.py
```

```bash
uv run configmap-colector.py
```

```bash
uv run deployments-colector.py
```

```bash
uv run experimento-colector.py podchaos
```

```bash
uv run experimento-colector.py stresschaos
```

`egress-colector.py` **no** es un watcher continuo — es un script de un solo
disparo. Córrelo aparte, una vez, cuando quieras (re)sembrar los nodos
`Egress`:

```bash
uv run egress-colector.py
```

El ingestor de incidencias (`ingestor-incidencias.py`) **no se levanta desde
aquí** — ya está desplegado de forma permanente dentro del clúster. Para
confirmar que sigue corriendo:

```bash
kubectl get pod ingestor-incidencias -n online-boutique
```

Si no existe o no está `Running`, hay que volver a desplegarlo (ver
`infra/README.md`, sección de ingesta de incidencias).

## 3. Disparar un experimento de caos

Con los colectores corriendo (orquestador u opción manual), aplica uno de
estos YAML con `kubectl apply -f <archivo>`. Hay un ejemplo guardado en
`pruebas/experimento-adservice.yaml` (pod-kill); los otros dos van abajo.

### Pod-kill (el escenario documentado original)

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: demo-podkill
  namespace: online-boutique
  annotations:
    pruebas/alerta-esperada: "DeploymentReplicasNoDisponibles"
    pruebas/deteccion-max-seg: "120"
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces: [online-boutique]
    labelSelectors:
      app: adservice
  duration: "30s"
```

Nota: `pod-kill` se recupera tan rápido que, con el intervalo de muestreo de
30s de Prometheus, normalmente **no** llega a disparar la alerta. Es un
resultado esperado, no un fallo del colector (ver sección 7 del TFM,
"Validación experimental").

### Pod-failure (para ver el ciclo completo de alerta disparando)

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: demo-podfailure
  namespace: online-boutique
  annotations:
    pruebas/alerta-esperada: "DeploymentReplicasNoDisponibles"
    pruebas/deteccion-max-seg: "120"
spec:
  action: pod-failure
  mode: one
  selector:
    namespaces: [online-boutique]
    labelSelectors:
      app: adservice
  duration: "60s"
```

### StressChaos — saturación de CPU

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: demo-stresscpu
  namespace: online-boutique
  annotations:
    pruebas/alerta-esperada: "CPUSaturada"
    pruebas/deteccion-max-seg: "150"
spec:
  mode: one
  selector:
    namespaces: [online-boutique]
    labelSelectors:
      app: adservice
  stressors:
    cpu:
      workers: 2
      load: 90
  duration: "150s"
```

Ojo con `load`: un valor muy alto (100) puede saturar tanto el contenedor que
falle sus *health checks* y se reinicie antes de que la alerta llegue a
dispararse — es justo la limitación documentada en el TFM. `load: 90` es más
estable.

### Limpieza después de un experimento

```bash
kubectl delete podchaos demo-podkill demo-podfailure -n online-boutique 2>/dev/null
kubectl delete stresschaos demo-stresscpu -n online-boutique 2>/dev/null
```

**Si vas a correr varios experimentos seguidos**, espácialos por más de 5
minutos entre sí (o usa componentes distintos) — si no, la ventana de
correlación del ingestor puede atribuir la misma alerta a más de un
experimento (ver "Validación experimental" en el TFM).

## 4. Verificar resultados en Neo4j

Desde `knowledge-graph/telemetry/` (necesita el port-forward del puerto 7687
activo):

```bash
python -c "
from shared import driver
with driver.session() as session:
    for r in session.run('MATCH (x:Experimento) RETURN x.nombre, x.accion, x.kind ORDER BY x.iniciado_en'):
        print(dict(r))
"
```

```bash
python -c "
from shared import driver
with driver.session() as session:
    for r in session.run('MATCH (i:Incidencia)-[c:CAUSADA_POR]->(x:Experimento) RETURN i.titulo, x.nombre, c.estado'):
        print(dict(r))
"
```

Si ves una fila con `estado: 'correlacionada'`, el ciclo completo (Chaos
Mesh → Prometheus → Alertmanager → ingestor → grafo) funcionó.

## 5. Consultas de validación (V1-V5)

Las cinco consultas completas están en `knowledge-graph/schema.md`, sección
8. Resumen de qué responde cada una:

| # | Pregunta |
|---|---|
| V1 | ¿Se detectó cada experimento y en cuánto tiempo, contra su SLO? |
| V2 | ¿Dispararon las alertas esperadas? ¿Hubo alertas inesperadas? |
| V3 | ¿Qué incidencias no las explica ningún experimento? |
| V4 | ¿Cuánto tardó el sistema en recuperarse? |
| V5 | ¿El impacto observado coincide con el radio de impacto que predice la topología? |

## 6. Limpiar datos de prueba en Neo4j

Si vas a repetir una campaña de experimentos desde cero (recomendado antes de
cada corrida limpia):

```bash
python -c "
from shared import driver
with driver.session() as session:
    print(session.run('MATCH (x:Experimento) DETACH DELETE x RETURN count(x) AS c').single())
    print(session.run('MATCH (i:Incidencia) DETACH DELETE i RETURN count(i) AS c').single())
"
```

Esto borra `Experimento` e `Incidencia` (y sus relaciones), pero no toca la
topología (`Pod`, `Deployment`, `Service`, etc.) ni el histórico de nodos
soft-deleted.

## 7. Solución de problemas

- **`kubectl` responde `Forbidden: unknown` o no responde:** el contenedor
  del control-plane de `kind` se reinició. Espera unos segundos y reintenta
  `kubectl get nodes`.
- **Un colector lleva rato corriendo y de repente empieza a fallar con
  errores de conexión/autenticación:** si el clúster se reinició *después*
  de que arrancaste el colector, su configuración de Kubernetes en memoria
  queda obsoleta. Hay que matarlo y volver a arrancarlo (o reiniciar el
  orquestador completo).
- **`kubectl port-forward` murió silenciosamente:** revisa con
  `ss -ltnp | grep 7687` (o `7474`); si no aparece nada, vuelve a lanzarlo.
- **Un colector dice "Connection error" en el log pero no está claro por
  qué:** ese mensaje genérico también puede estar escondiendo un bug real de
  código (no solo problemas de red) — ver la nota correspondiente en
  `knowledge-graph/telemetry/shared_chaos.py`. Si sospechas esto, reproduce
  el evento a mano llamando `structure_event`/`insert_event` directamente
  contra un objeto real (`kubectl get <recurso> -o json`), fuera del ciclo
  de watch, para ver el error de verdad.
