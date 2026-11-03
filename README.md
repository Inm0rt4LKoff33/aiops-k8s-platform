# AIOps Kubernetes Platform

TFM — Máster Universitario en Análisis y Visualización de Datos Masivos (UNIR).
Plataforma de análisis, visualización y diagnóstico predictivo de incidentes en
infraestructura Kubernetes mediante un Knowledge Graph (Neo4j) y un servidor MCP.

## Arquitectura

```
Telemetría del clúster (logs, métricas, eventos, configs)
        ↓
Pipeline de procesamiento a escala (PySpark / batch histórico)
        ↓
Knowledge Graph en Neo4j (topología + relaciones + incidentes correlacionados)
        ↓
    ├── Análisis: detección de anomalías, causa raíz, predicción
    ├── Dashboard web interactivo (visualización del grafo + métricas + timeline)
    └── Servidor MCP → agente de IA (diagnóstico conversacional)

Todo desplegado sobre Kubernetes
```

## Estructura del repositorio

- `infra/` — configuración del clúster, aplicación de referencia, chaos engineering
- `pipeline/` — ingesta y procesamiento de telemetría (PySpark)
- `knowledge-graph/` — esquema y carga del grafo en Neo4j
- `analysis/` — detección de anomalías, análisis de causa raíz, modelo predictivo
- `dashboard/` — visualización web interactiva
- `mcp-server/` — servidor MCP que expone el grafo y el análisis a un agente de IA

## Entorno de datos

No se dispone de acceso a infraestructura real de una empresa, así que los datos
se generan desplegando [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo)
(aplicación de referencia de microservicios de Google, con interdependencias
realistas) sobre un clúster Kubernetes local (`kind`), instrumentado con una
pila de observabilidad equivalente a producción, y sometido a fallos
controlados mediante chaos engineering para generar incidentes con causa raíz
conocida (ground truth).

## Estado actual

- [x] Clúster Kubernetes local (`kind`) desplegado
- [x] Online Boutique desplegado y generando tráfico sintético realista
- [ ] Pila de observabilidad (Prometheus, agregador de logs)
- [ ] Inyección de fallos con chaos engineering
- [ ] Pipeline de ingesta/procesamiento (PySpark)
- [ ] Knowledge Graph (Neo4j)
- [ ] Análisis (anomalías, causa raíz, predicción)
- [ ] Dashboard de visualización
- [ ] Servidor MCP
