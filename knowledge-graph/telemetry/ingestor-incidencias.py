from flask import Flask, request, jsonify
from neo4j import GraphDatabase

NEO4J_URI = "bolt://neo4j.knowledge-graph.svc:7687"
NEO4J_AUTH = ("neo4j", "aiops-tfm-2026")

driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

import logging

logger = logging.getLogger(__name__)
app = Flask(__name__)

@app.route("/alertmanager", methods=["POST"])
def alertmanager_webhook():
    response = request.get_json()

    if response is None:
        return jsonify({"error": "Invalid JSON"}), 400

    insert_incidencia(driver, response)
    return jsonify({"status": "ok"})

def insert_incidencia(driver, w):
    with driver.session() as session:
        session.run("""
            WITH $w AS w
            MERGE (i:Incidencia {alerta_grupo: w.groupKey})
            ON CREATE SET i.id           = randomUUID(),
                            i.titulo       = w.groupLabels.alertname + ' · ' + w.groupLabels.namespace,
                            i.severidad    = CASE w.commonLabels.severity
                                            WHEN 'critical' THEN 'SEV1'
                                            WHEN 'warning'  THEN 'SEV3'
                                            ELSE 'SEV4' END,
                            i.estado       = 'abierta',
                            i.origen       = 'alertmanager',
                            i.detectada_en = datetime(w.alerts[0].startsAt)
            WITH i, w
            UNWIND w.alerts AS a
            WITH i, a, a.labels AS l

            CALL {
            WITH l
            OPTIONAL MATCH (p:Pod        {namespace: l.namespace, nombre: l.pod})
            OPTIONAL MATCH (d:Deployment {namespace: l.namespace, nombre: l.deployment})
            OPTIONAL MATCH (s:Service    {namespace: l.namespace, nombre: l.service})
            OPTIONAL MATCH (g:Ingress    {namespace: l.namespace, nombre: l.ingress})
            OPTIONAL MATCH (e:Egress     {destino: l.instance})
            RETURN coalesce(p, d, s, g, e) AS o
            }
            WITH i, a, o WHERE o IS NOT NULL
            MERGE (i)-[r:AFECTA {alerta_fingerprint: a.fingerprint}]->(o)
            ON CREATE SET r.alertname = a.labels.alertname,
                            r.desde     = datetime(a.startsAt),
                            r.sintoma   = a.labels.reason
            SET r.hasta = CASE a.status WHEN 'resolved' THEN datetime(a.endsAt) ELSE null END

            WITH i, o, r
            MATCH (x:Experimento)
            WHERE r.desde >= x.iniciado_en
            AND r.desde <= coalesce(x.finalizado_en, datetime()) + duration({minutes: 5})
            AND (
                    EXISTS { (x)-[:INYECTADO_EN]->(o) }
                OR EXISTS { (x)-[:INYECTADO_EN]->(:Pod)<-[:SELECCIONA|GESTIONA]-(o) }
                OR EXISTS { (x)-[:INYECTADO_EN]->(:Pod)<-[:SELECCIONA]-(:Service)<-[:ENRUTA_A]-(o) }
                OR EXISTS { (x)-[:INYECTADO_EN]->(:Pod)<-[:SELECCIONA]-(:Service)<-[:DEPENDE_DE {critica: true}]-(o) }
                OR EXISTS { (x)-[:INTERFIERE_CON]->(o) }
            )
            MERGE (i)-[c:CAUSADA_POR]->(x)
            ON CREATE SET c.estado = 'correlacionada'
        """, w=w)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)