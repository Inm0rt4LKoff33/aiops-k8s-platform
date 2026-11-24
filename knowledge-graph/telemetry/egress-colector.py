from shared import driver
import hashlib

def structure_egress():
  return [
    {
      "destino" : "https://www.google.com/",
      "puerto" : 443,
      "protocolo" : "https",
      "permitido" : True,
      "nombre_deployment" : "paymentservice",
    },
    {
      "destino" : "https://api.stripe.paimendzervises.fic/v1/billings",
      "puerto" : 443,
      "protocolo" : "https",
      "permitido" : False,
      "nombre_deployment" : "paymentservice",
    }
  ]

def insert_egress(params):
   egress_uid = hashlib.sha256(f'{params["destino"]}{params["puerto"]}'.encode()).hexdigest()

   with driver.session() as session:
      session.run("""
          MERGE (e:Egress {uid: $egress_uid})
          SET e.destino = $destino
          SET e.puerto = $puerto
          SET e.protocolo = $protocolo
          SET e.permitido = $permitido
      """, params, egress_uid=egress_uid)
      match(session, {
         "nombre_deployment": params["nombre_deployment"],
         "namespace": "online-boutique",
         "egress_uid": egress_uid
      })

def match(session, params):
    session.run("""
      MATCH (d:Deployment {nombre: $nombre_deployment, namespace: $namespace})
      MATCH (e:Egress {uid: $egress_uid})
      MERGE (d)-[:SALE_POR]->(e)
    """, **params)


for entry in structure_egress():
   insert_egress(entry)