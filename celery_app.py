from celery import Celery
import os
import time

REDIS_HOST= os.getenv("REDIS_HOST","localhost")
REDIS_PORT= os.getenv("REDIS_PORT","6379")
REDIS_URL= f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    "tarefas_livros",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_track_started=True,
    result_expires = 3600,
    result_persistent=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"]
)

#TAREFA SOMAR QUE SOMA DOIS NUMEROS 
@celery_app.task(name="tasks.somar")
def somar(n1: int, n2: int):
    time.sleep(3)
    return n1+n2

#TAREFA QUE CALCULA O FATORIAL DE UM NUMERO 
@celery_app.task(name="tasks.fatorial")
def fatorial(n: int):
    time.sleep(3)
    if n < 0:
        raise ValueError("Numero negativo, não é possível calcular")
    
    resultado = 1
    for i in range(2,n+1):
        resultado *= i
    return resultado

