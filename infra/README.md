# Infraestructura

Herramientas de terceros desplegadas vía Helm/kubectl — no código original del
TFM, documentado aquí por trazabilidad.

## Clúster
- `kind create cluster --name aiops-platform`

## Aplicación de referencia
- Online Boutique (Google): `kubectl apply -n online-boutique -f https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/main/release/kubernetes-manifests.yaml`

## Observabilidad (namespace `observability`)
- `kube-prometheus-stack` (Prometheus + Grafana + Alertmanager + node-exporter + kube-state-metrics)
- `loki-stack` (Loki + Promtail) para logs

## Inyección de fallos (namespace `chaos-mesh`)
- Chaos Mesh 2.7.2, vía Helm chart oficial (`chaos-mesh/chaos-mesh`)
- `chaosDaemon.runtime=containerd` y `chaosDaemon.socketPath=/run/containerd/containerd.sock`, acorde al runtime del clúster `kind`
- Los experimentos corren directamente sobre `online-boutique` (no sobre un namespace `chaos-test` separado): se reutiliza el `adservice` real, ya con tráfico del `loadgenerator` propio de Online Boutique

## Regla de alerta y recepción de incidencias (namespace `online-boutique`)
- `PrometheusRule` `chaos-online-boutique`: regla `DeploymentReplicasNoDisponibles`
  (`kube_deployment_status_replicas_unavailable{namespace="online-boutique"} > 0`,
  `for: 10s`), con la etiqueta `release: kube-prometheus` que exige el
  `ruleSelector` del operador.
- `ingestor-incidencias.py` corre dentro del clúster como un Pod (imagen
  `python:3.12-slim` + `pip install flask neo4j` al arrancar, script montado
  vía ConfigMap `ingestor-incidencias-script`) con su propio Service
  (`ingestor-incidencias.online-boutique.svc:8080`) — no se ejecuta desde el
  host como los demás colectores, porque Alertmanager necesita poder
  alcanzarlo desde dentro del clúster.
- `AlertmanagerConfig` `chaos-ingestor` (namespace `online-boutique`): enruta
  las alertas de `online-boutique` hacia `ingestor-incidencias` vía webhook
  (`/alertmanager`). El operador la recoge automáticamente porque
  `alertmanagerConfigSelector`/`alertmanagerConfigNamespaceSelector` del
  `Alertmanager` están vacíos (sin filtro).

## Grafo de conocimiento (namespace `knowledge-graph`)
- Neo4j 2026.10.1 Community Edition, vía Helm chart oficial (`neo4j/neo4j`)
- Servicio de tipo LoadBalancer deshabilitado (`services.neo4j.enabled=false`) — no aplica en un clúster `kind` local sin balanceador; se accede vía `kubectl port-forward`
- Credenciales en el values de Helm (uso local/académico; para producción usar `neo4j.passwordFromSecret`)

Nota: se eliminaron dos contenedores Docker standalone de Neo4j (`neo4j`, `affectionate_burnell`) creados en una exploración previa fuera de Kubernetes, para evitar tener dos instancias redundantes del grafo. Se optó por la instancia en Kubernetes por consistencia con el objetivo de contenerizar toda la plataforma.
