import sys
import re
import subprocess
import shutil
import urllib.request
import urllib.error
import json
import os
from pathlib import Path
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from . import rag   
#from rag import consultar_documentacion 

cwd = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_RETRIES = 10
current_retries = 0
best_mas_state = {}
best_error_count = float('inf')


def resolve_jason_command():
    """
    Busca el ejecutable de Jason en este orden:
    1. Variable de entorno JASON_BIN
    2. Comando 'jason' disponible en el PATH
    3. Ruta típica de macOS (/Applications/jason)
    4. Ruta típica de Windows (C:\\Jason\\bin\\jason.bat)
    """
    env_path = os.getenv("JASON_BIN")
    if env_path:
        return env_path

    path_command = shutil.which("jason")
    if path_command:
        return path_command

    default_macos_path = "/Applications/jason"
    if Path(default_macos_path).exists():
        return default_macos_path

    default_windows_paths = [
        r"C:\Jason\bin\jason.bat",
        r"C:\Program Files\Jason\bin\jason.bat",
        r"C:\Program Files (x86)\Jason\bin\jason.bat",
    ]
    for windows_path in default_windows_paths:
        if Path(windows_path).exists():
            return windows_path

    return None

def search_github_examples(path: str = "", category: str = "examples") -> str:
    """
    Accede a diferentes fuentes de código e información de Jason en GitHub.
    
    Args:
        path: Ruta relativa del archivo o directorio.
        category: 
            - 'examples': Ejemplos oficiales (blocks, auction, etc.) [Por defecto].
            - 'demos': Demostraciones de características específicas.
            - 'applications': Proyectos y aplicaciones reales de la comunidad.
            - 'kernel': Código interno de Jason (útil para entender el funcionamiento avanzado).
    """

    # Elimina del principio de `path` el contenido de `category`, que a veces la IA se confunde.
    path = re.sub(rf"^{category}\/", "", path)

    # Mapeo de categorías a URLs de la API de GitHub
    SOURCES = {
        "examples": "https://api.github.com/repos/jason-lang/jason/contents/examples",
        "demos": "https://api.github.com/repos/jason-lang/jason/contents/demos",
        "applications": "https://api.github.com/repos/jason-lang/jason-applications/contents",
        "kernel": "https://api.github.com/repos/jason-lang/jason/contents/src/jason"
    }
    
    base_url = SOURCES.get(category, SOURCES["examples"])
    url = f"{base_url}/{path}".strip("/")
    
    try:
        # Mantenemos la lógica original de urllib y manejo de JSON
        req = urllib.request.Request(url, headers={'User-Agent': 'Python-urllib'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if isinstance(data, list):
                items = [f"[{item['type']}] {item['path']}" for item in data]
                return f"Contenido en {category}/{path}:\n" + "\n".join(items)
            
            elif isinstance(data, dict) and data.get("type") == "file":
                download_url = data.get("download_url")
                if download_url:
                    req_file = urllib.request.Request(download_url, headers={'User-Agent': 'Python-urllib'})
                    with urllib.request.urlopen(req_file) as f_res:
                        return f_res.read().decode('utf-8')
                return "Error: No se encontró la URL de descarga."
            return "Respuesta inesperada de GitHub."
                
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"Error: No se encontró '{path}' en la categoría '{category}'."
        return f"Error HTTP: {e.code}"
    except Exception as e:
        return f"Error: {e}"

def test_mas_code(mas2j_code: str, agents_dict: dict) -> str:
    """
    Guarda y ejecuta el código en un directorio temporal para probar el sistema Multi-Agente usando jason.
    NO guarda los archivos definitivamente, solo devuelve la salida para que verifiques si funciona.
    Tiene un límite de 10 intentos por sesión.
    
    Args:
        mas2j_code: El contenido completo del archivo de configuración .mas2j.
        agents_dict: Un diccionario donde la clave es el nombre del archivo (ej. "agent1.asl") 
                     y el valor es el contenido de ese archivo .asl.
    """
    global current_retries, best_mas_state, best_error_count
    
    if current_retries >= MAX_RETRIES:
         return f"ERROR: Has superado el límite de {MAX_RETRIES} intentos. Por favor, utiliza 'save_mas_code' para guardar el último código de inmediato y termina tu respuesta."
         
    current_retries += 1
    
    temp_dir = Path("temp_mas_project")
    
    try:
        # Limpiar si ya existe
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        # Guardar .mas2j
        mas2j_file = temp_dir / "temp.mas2j"
        mas2j_file.write_text(mas2j_code, encoding="utf-8")
        
        # Guardar archivos .asl
        for filename, content in agents_dict.items():
            if not filename.endswith(".asl"):
                filename += ".asl"
            (temp_dir / filename).write_text(content, encoding="utf-8")
            
        jason_command = resolve_jason_command()
        if not jason_command:
            return (
                "ERROR: No se ha encontrado Jason. Instálalo y define la variable "
                "de entorno JASON_BIN o añade el comando 'jason' al PATH."
            )

        result = subprocess.run(
            [jason_command, "mas", "start", "--mas2j=temp.mas2j", "--console"],
            cwd=str(temp_dir),
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Heurística simple para contar errores basándonos en STDERR y el código de retorno
        error_count = 0
        if result.returncode != 0:
            error_count += 10
        if result.stderr:
            error_count += len(result.stderr.split('\n'))
            
        if error_count < best_error_count:
            best_error_count = error_count
            best_mas_state = {
                "mas2j": mas2j_code,
                "agents": agents_dict
            }
            
        # Format output
        output = f"=== EJECUCIÓN DE PRUEBA (Intento {current_retries}/{MAX_RETRIES}) ===\nReturn code: {result.returncode}\n"
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"

        # limita los caracteres para no superar el máximo de tokens
        return output[:10000] + "\n === FIN DE EJECUCIÓN === "
        
    except subprocess.TimeoutExpired as e:
        # En muchos sistemas, jason arranca la GUI y se queda pillado. Guardamos el estado.
        if best_error_count == float('inf'):
            best_mas_state = {
                "mas2j": mas2j_code,
                "agents": agents_dict
            }
            
        output = f"=== EJECUCIÓN DE PRUEBA (Intento {current_retries}/{MAX_RETRIES}) ===\n"
        output += "AVISO: La ejecución alcanzó el tiempo límite (15s). Esto es normal si Jason arranca una interfaz y no finaliza solo.\n"
        if hasattr(e, 'stdout') and e.stdout:
            stdout_str = e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else e.stdout
            output += f"--- STDOUT (parcial) ---\n{stdout_str}\n"
        if hasattr(e, 'stderr') and e.stderr:
            stderr_str = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr
            output += f"--- STDERR (parcial) ---\n{stderr_str}\n"
        return output
        
    except FileNotFoundError:
        return "ERROR: El comando 'jason' no se encuentra en el sistema. Asegúrate de tener instalado Jason y agregado al PATH."
    except Exception as e:
        return f"ERROR inesperado al ejecutar: {e}"
    finally:
        # Limpiar
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def save_mas_code(mas_name: str, mas2j_code: str = "", agents_dict: dict|None = None) -> str:
    """
    Guarda el sistema MAS completo (el .mas2j y los .asl) en su propia subcarpeta dentro de 'output'.
    Si provees 'mas2j_code' y 'agents_dict', guardará esos. Si están vacíos, usará el 'mejor' código que lograste ejecutar en tus pruebas.
    
    Args:
        mas_name: Nombre del proyecto (se usará para la subcarpeta en 'output' y el archivo .mas2j).
    """
    global current_retries, best_mas_state, best_error_count
    
    if agents_dict is None:
        agents_dict = {}
        
    project_dir = OUTPUT_DIR / mas_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    code_mas2j = mas2j_code if mas2j_code else best_mas_state.get("mas2j", "")
    code_agents = agents_dict if agents_dict else best_mas_state.get("agents", {})
    
    if not code_mas2j or not isinstance(code_agents, dict) or not code_agents:
         return "ERROR: No hay código generado para guardar o no se ha probado previamente."
         
    try:
        # Guardar .mas2j
        mas_filename = f"{mas_name}.mas2j" if not mas_name.endswith(".mas2j") else mas_name
        (project_dir / mas_filename).write_text(str(code_mas2j), encoding="utf-8")
        
        # Guardar .asl
        for filename, content in code_agents.items():
            if not filename.endswith(".asl"):
                filename += ".asl"
            (project_dir / filename).write_text(str(content), encoding="utf-8")
        
        # Resetear estado para próximas llamadas del usuario
        current_retries = 0
        best_mas_state = {}
        best_error_count = float('inf')
        
        return f"ÉXITO: Proyecto BDI guardado correctamente en {project_dir}"
    except Exception as e:
        return f"ERROR inesperado al guardar: {e}"

def calculate_fibonacci(n: int) -> str:
    """
    Calcula los primeros 'n' números de la secuencia de Fibonacci. 
    Útil cuando el usuario pide lógica matemática compleja o ejemplos de algoritmos.
    
    Args:
        n: La cantidad de números de la secuencia a generar.
    """
    if n <= 0:
        return "Por favor, solicita un número mayor a 0."
    
    sequence = [0, 1]
    while len(sequence) < n:
        # Fórmula: $F_n = F_{n-1} + F_{n-2}$
        sequence.append(sequence[-1] + sequence[-2])
    
    result = sequence[:n]
    return f"Los primeros {n} números de Fibonacci son: {result}"

def get_instructions(filename: str):
    return open(Path(cwd, "instructions", filename), encoding="utf-8").read()

def exit_loop(tool_context: ToolContext):
    print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    return "Programa finalizado. Ahora sólo queda guardar."

# Configuramos el modelo, asumiendo la configuración habitual
model = LiteLlm(
    #model="openai/gpt-oss-120b", 
    # model= "openai/Qwen3.6-35B-A3B-FP8",
    model="openai/poligpt-code",
    api_base="https://api.poligpt.upv.es/",
    api_key="sk-LFXs1kjaSxtEDgOMlPUOpA"
)

web_searcher = LlmAgent(
    name="Web_Searcher",
    description="Agente buscador de ejemplos de lenguaje Jason",
    model=model,
    tools=[search_github_examples],
    output_key="examples",
    instruction=get_instructions("web_searcher.md")
)

doc_searcher = LlmAgent(
    name="Doc_Searcher",
    description="Agente buscador de documentación local sobre el lenguaje Jason",
    model=model,
    tools=[rag.search_local_docs],
    output_key="documentation",
    instruction=get_instructions("doc_searcher.md")
)

aggregator = ParallelAgent(
    name="Aggregator",
    description="Agente recopilador de información sobre el lenguaje Jason en diversas fuentes",
    sub_agents = [web_searcher, doc_searcher]
)

coder = LlmAgent(
    name="Coder",
    description="Agente programador experto en sistemas Multi-Agente en Jason",
    model=model,
    tools=[calculate_fibonacci],
    output_key="agent_code",
    instruction=get_instructions("coder.md")
)

# validator = LoopAgent(
#     name="Validator",
#     description="Agente validador experto en el lenguaje Jason. Comprueba si el código Jason sigue todas las reglas sintácticas y semánticas",
#     sub_agents=[coder],
#     max_iterations=5
# )

tester = LlmAgent(
    name="Tester",
    description="Agente testeador. Ejecuta sistemas Multi-Agente y comprueba si el funcionamiento es correcto",
    model=model,
    tools=[test_mas_code, exit_loop],
    output_key="fixes",
    instruction=get_instructions("tester.md")
)

refiner = LoopAgent(
    name="Refiner",
    description=(
        "Agente refinador. "
        "Repite el proceso de desarrollo hasta que el resultado del sistema Multi-Agente válido de acuerdo a las especificaciones del usuario."
    ),
    sub_agents=[aggregator, coder, tester],
    max_iterations=10
)

saver = LlmAgent(
    name="Saver",
    description="Su único trabajo es guardar el código Multi-Agente generado",
    model=model,
    tools=[save_mas_code],
    output_key="save_info",
    instruction=get_instructions("saver.md")
)

root_agent = SequentialAgent(
    name="BDI_Developer",
    description="Pipeline completo para el desarrollo proyectos Multi-Agente BDI en Jason: investigación → programación → validación → testeo → guardado",
    sub_agents=[refiner, saver]
)

# root_agent = LlmAgent(
#     name="BDI_Developer",
#     model=model,
#     description="Agente experto en desarrollador proyectos Multi-Agente BDI en Jason",
#     instruction=open(Path(cwd, "instructions.md"), encoding="utf-8").read(),
#     tools=[search_github_examples, rag.search_local_docs, test_mas_code, save_mas_code, calculate_fibonacci],
# )
