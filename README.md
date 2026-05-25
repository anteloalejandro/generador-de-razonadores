# Generador de Razonadores BDI

Este repositorio contiene código para, mediante `google-adk`, generar agentes BDI en lenguaje JASON.

- Numero fibonacci
- Pregunta-respuesta "Ping Pong"
- Subasta holandesa

## Setup

***AVISO: JASON sólo funciona en máquinas con `bash` u otro shell POSIX disponible***

Instalar JAVA 21

Instalar JASON

Instalar los requisitos (haciendo primero un `venv` si se considera conveniente)
```bash
pip install -r agent/requirements.txt
```

Actualizar el RAG
```bash
cd agent
python update_rag.py
cd ..
```
