#IMPORTS PARA API FUNCIONAR
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy import create_engine, Column, Integer, String
import redis
import json
from celery_app import fatorial, somar
import os
from kafka_producer import enviar

dicionario = {}
app = FastAPI()
base = declarative_base()
database_url = "sqlite:///./atividadeawait.db"
engine =  create_engine(database_url, connect_args={"check_same_thread":False})
SessionLocal = sessionmaker(autocommit = False, autoflush= False, bind = engine)
REDIS_HOST = os.getenv("REDIS_HOST","localhost")
REDIS_PORT = os.getenv("REDIS_PORT","6379")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

#INICIA SESSAO
def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
     db.close()

#CLASSES PARA CRIAÇÃO DOS LIVROS
class LivroDB(base):
    __tablename__ = "Livros"
    id = Column(Integer, index = True, primary_key = True)
    nome_livro = Column(String, index = True)
    autor_livro =Column(String, index = True)

class Livros(BaseModel):
    nome_livro: str
    autor_livro: str

base.metadata.create_all(bind = engine)

#AS DUAS FUNÇÕES ASSINCROONAS UMA PARA SALVAR OS LIVROS E MOSTRAR COM UM TIMER DE 30SEGUNDOS
#A OUTRA SOMENTE DELETA O LIVRO QUE A PESSOA QUISER EXCLUIR
async def salvar_livros_redis(livro_id:int, livro: Livros):
   redis_client.set(f"livro:{livro_id}", json.dumps(livro.model_dump()), ex=30)

async def deletar_livros_redis(id:int):
   redis_client.delete(f"livro:{id}")

#CRIEI UMA FUNCAO PARA RETORNAR UMA MENSAGEM USANDO O AWAIT
async def sistema(mensagem: str):
   await asyncio.sleep(2)
   print(f"Log:{mensagem}")

@app.post("/calcular/soma")

#FUNCAO PARA CALCULAR A SOMA DE DOIS NUMEROS
async def calcular_soma(n1: int, n2: int):
   tarefa = somar.delay(n1,n2)
   redis_client.lpush("tarefas_ids", tarefa.id)
   return {"task_id": tarefa.id,"message":"tarefa de soma iniciada"}

@app.post("/calcular/fatorial")

#FUNCAO PARA CALCULAR O FATORIAL DE UM NUMERO
async def calcular_fatorial(n: int):
   tarefa = fatorial.delay(n)
   redis_client.lpush("tarefas_ids", tarefa.id)
   return {"task_id": tarefa.id, "message": "tarefa execucao"}

@app.get("/debug/redis")

#FUNCAO PARA LISTAR OS LIVROS NO FORMATO CHAVE, VALOR
async def ver_livros():
    chaves = redis_client.keys("*")
    livros = []

    for chave in chaves:
        valor = redis_client.get(chave)
        ttl= redis_client.ttl(chave)

        livros.append({"chave": chave,"valor": json.loads(valor), "ttl": ttl })
      
    return livros

@app.get("/livros")
#FUNCAO ASSINCRONA DE LISTAR OS LIVROS, SE ESTIVER VAZIA VAI RETORNAR QUE NAO TEM NADA, SE NAO VAI SÓ VOLTAR OS LIVROS LISTADOS
async def get_livros(db: Session = Depends(sessao_db)):
    #COLOQUEI EM PRIMEIRO PARA VERIFICAR O CACHE
    cache_key = "lista_livros"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    await sistema(f"Procurando livros")

    #BUSCA OS LIVROS POR OREDEM ALFABETICA
    livros = db.query(LivroDB).order_by(LivroDB.nome_livro).all()

    if not livros:
       return {"message": "Nenhum livro encontrado"}
    
    #CRIEI UMA LISTA PARA EXIBIR OS LIVROS COM O ID EM PRIMEIRO, JÁ QUE NA HORA DE ATUALIZAR
    #E DELETAR A GENTE BUCA PELO ID, ACHO QUE FICA VISUALMENTE MAIS AGRADAVEL ASSIM
    lista = []
    for livro in livros:
       lista.append({
          "ID": livro.id,
          "Nome do Livro": livro.nome_livro,
          "Autor do Livro": livro.autor_livro
       })

    redis_client.setex(cache_key, 30, json.dumps(lista))

    return lista

@app.post("/livros")
#FUNCAO ASSINCRONA DE ADICIONAR LIVROS, PESQUISA SE O LIVRO JÁ EXISTE PELO NOME SE JÁ EXISTIR RETORNA MENSAGEM QUE JÁ TEM
#SE NAO TIVER ELE VAI ADICIONAR E RETORNAR MENSAGEM
async def post_livros(livros: Livros, db: Session = Depends(sessao_db)):
   livro = db.query(LivroDB).filter(LivroDB.nome_livro == livros.nome_livro, LivroDB.autor_livro == livros.autor_livro).first()
   if livro:
      raise HTTPException (status_code=400, detail="Livro já está na sua lista")
   
   await sistema(f"Adicionando livro")
   
   novo_livro = LivroDB(nome_livro=livros.nome_livro,autor_livro=livros.autor_livro)

   db.add(novo_livro)
   db.commit()
   db.refresh(novo_livro)

   await salvar_livros_redis(novo_livro.id,livros)
   #LIMPA O CACHE DA LISTA PARA ATUALIZAR A ROTA GET
   redis_client.delete("lista_livros")

   #CHAMA FUNÇÃO DO ARQUIVO KAFKA PARA EXIBIR OS LIVROS
   enviar("livros_eventos",{
      "Ação": "criar",
      "Livro": livros.dict()
   })

   return {"message": "Livro adicionado"}

@app.put("/livros/{id}")
#FUNCAO ASSINCRONA DE ATUALIZAR LIVROS, PESQUISA PELO ID SE LIVRO EXISTE
#SE NAO EXISTIR LANÇA ERRO FALANDO QUE NAO FOI ENCONTRADO, SE SIM ATUALIZA E RETORNA MENSAGEM DE OK
async def put_livros(id: int,livros_input: Livros, db: Session = Depends(sessao_db)):
   livro = db.query(LivroDB).filter(LivroDB.id == id).first()
   if not livro:
       raise HTTPException(status_code=404, detail="Livro nao encontrado")
   
   await sistema(f"Atualizando dados do livro")

   #PASSA O INPUT PYDANTIC PARA REDIS
   livro.nome_livro = livros_input.nome_livro
   livro.autor_livro = livros_input.autor_livro
   db.commit()
   db.refresh(livro)

   await salvar_livros_redis(id, livros_input)
   redis_client.delete("lista_livros")

   return{"message": "Livro atualizado"}

@app.delete("/livros/{id}")
#FUNCAO ASSINCRONA DE DELETAR, PESQUISA PELO ID SE O LIVRO EXISTE
#SE NÃO EXISTIR LANÇA UM ERRO, SE EXISTIR EXCLUI E RETORNA MENSAGEM
async def delete_livros(id: int, db: Session = Depends(sessao_db)):
   livro = db.query(LivroDB).filter(LivroDB.id == id).first()

   if not livro:
        raise HTTPException(status_code=404, detail="livro não encontrado")
       
   await sistema (f"Deletando o livro")
   
   db.delete(livro)
   db.commit()

   await deletar_livros_redis(id)
   redis_client.delete("lista_livros")

   return{"message": "Livro excluido"}

