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

## Pendiente
- Chaos Mesh para inyección de fallos

## Grafo de conocimiento (namespace `knowledge-graph`)
- Neo4j 2026.10.1 Community Edition, vía Helm chart oficial (`neo4j/neo4j`)
- Servicio de tipo LoadBalancer deshabilitado (`services.neo4j.enabled=false`) — no aplica en un clúster `kind` local sin balanceador; se accede vía `kubectl port-forward`
- Credenciales en el values de Helm (uso local/académico; para producción usar `neo4j.passwordFromSecret`)

Nota: se eliminaron dos contenedores Docker standalone de Neo4j (`neo4j`, `affectionate_burnell`) creados en una exploración previa fuera de Kubernetes, para evitar tener dos instancias redundantes del grafo. Se optó por la instancia en Kubernetes por consistencia con el objetivo de contenerizar toda la plataforma.
