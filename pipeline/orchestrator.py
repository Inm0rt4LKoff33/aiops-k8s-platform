import subprocess
import signal
import sys
import time

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent        # la carpeta pipeline/, sin importar desde dónde se ejecutó
TELEMETRY_DIR = BASE_DIR.parent / "knowledge-graph" / "telemetry"  # sube un nivel y baja a telemetry/

commands_list = [
  ["uv", "run", "pod-colector.py"], 
  ["uv", "run", "service-colector.py"], 
  ["uv", "run", "ingress-colector.py"], 
  ["uv", "run", "configmap-colector.py"],
  ["uv", "run", "deployments-colector.py"],
  ["uv", "run", "experimento-colector.py", "podchaos"],
  ["uv", "run", "experimento-colector.py", "stresschaos"]
]


def start_up_subprocesses(commands_list):
  result = []
  for command in commands_list:
    result.append({
      "comando" : command,
      "proceso" : subprocess.Popen(cwd=TELEMETRY_DIR, args=command)
      })

  return result

def health_check_subprocesses(processes):
  for process in processes:
    if process["proceso"].poll() is not None:
      process["proceso"] = subprocess.Popen(cwd=TELEMETRY_DIR, args=process['comando'])

def handle_shutdown(signum, frame):
  terminate_subprocesses(processes)
  sys.exit(0)

def terminate_subprocesses(processes):
  for process in processes:
    process["proceso"].terminate()

processes = start_up_subprocesses(commands_list)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

while(True):
  health_check_subprocesses(processes)
  time.sleep(15)