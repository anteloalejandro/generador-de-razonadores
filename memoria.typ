#import "@preview/ilm:2.0.0": *
#import "@preview/calloutly:1.0.0" : callout-style, callout, note, tip, important, warning, caution

#set text(lang: "es")
#set figure(supplement: "Figura")

#show: ilm.with(
  title: "Arquitectura del Agente Generador de Razonadores",
  authors: ("Alejandro Antelo Fashoro", "Pau Riera Ribas"),
  date: datetime.today(),
  date-format: "[day] / [month] / [year repr:full]",
  raw-text: "use-typst-default",
  table-of-contents: none,
  external-link-circle: false,
  chapter-pagebreak: false,
  footer: "page-number-center",
  paper-size: "a4",
)

#show: callout-style.with(style: "quarto")

= Introducción

Este es un agente de IA que genera agentes BDI en lenguaje JASON capaces de comunicarse entre sí.

El objetivo es hacer que el IA genere los siguientes 3 tipos de agente:

+ *Agente fibonacci*, que imprime los primeros números indicados de la secuencia fibonacci.

+ *Agentes ping-pong*, donde uno de ellos manda mensajes que el otro responde, un número indicado de veces.

+ *Subasta holandesa*, donde varios agentes se comunican para pujar por un producto.

= Arquitetcuta Multiagente

Hemos optado por la siguiente arquitectura Multiagente para mejorar el rendimiento, separación de preocupaciones, y consistencia de las respuestas generadas y del ciclo de desarrollo de los agentes:

```
           ╭── Web_Searcher ──╮
INICIO ─┬──┤                  ├── Coder ─── Tester ──┬─ FIN
        │  ╰── Doc_Searcher ──╯                      │
        │                                            │
        ╰────────────────────────────────────────────╯
```

- `Web_Searcher` se ocupa de buscar documentación online en github.
- `Doc_Searcher` se ocupa de buscar en la documentación local.
- `Coder` se encarga de programar el propio agente.
- `Tester` se limita a probar el código, evaluar su validez, y decidir si se debe empezar el desarrollo de nuevo o no.

Los dos _Searcher_ se ejecutan en paralelo porque no dependen el uno del otro, y así reducimos el impacto que tiene la latencia de las respuestas (y en el caso del `WebSearcher`, la latencia de la búsqueda online).

Sólo después de que ambos _Searcher_ hayan buscado su documentación, el `Coder` pasa a desarrolar a los agentes BDI.

Cuando se ha generado el código de los Agentes, el `Tester` lo ejecuta y mira tanto la entrada como la salida estándar de la ejecución, y comprueba que no haya errores y que si funciona lo hace de acuerdo a las especificaciones del usuario. Si no se da el caso, se empieza el proceso de nuevo, pero si se da, guarda el código y finaliza el ciclo de desarrollo.

= _Tools_

Los agentes cuentan con las siguientes _tools_:

- `Web_Searcher`
  - ```python search_github_examples(path: str = "", category: str = "examples")```: Busca ejemplos relevantes en la documentación online de JASON.
- `Doc_Searcher`
  - ```python search_local_docs(query: str, k: int = 4)```: Busca en la documentación local (curada por nosotros) información sobre el lenguaje JASON.
- `Coder`
  - ```python calculate_fibonacci(n: int)```: Saca los `n` primeros números de la secuencia fibonacci, para que el modelo de IA tenga una referencia de lo que debe sacar el agente fibonacci.
- `Tester`
  - ```python test_mas_code(mas2j_code: str, agents_dict: dict)```: Comprueba el funcionamiento de los agentes en JASON, mostrando la salida o los posibles errores sintácticos y semánticos.
  - ```python exit_loop(mas_name: str, tool_context: ToolContext)```: Guarda el proyecto generado durante el testeo y sale del bucle usando `tool_context`.

Una de las _tools_ más importantes de `test_mas_code`, pues es lo que permite que funcione el desarrollo iterativo; sin ella el agente no sabe si lo que ha hecho está bien o mal, y no actúa correctamente. Sin embargo, esta función tenía un problema: Sólo muestra la salida estándar, y tanto los errores como los resultados salen por *error estándar* cuando la ejecución no termina a tiempo. El arreglo es sencillo:

```python
if hasattr(e, 'stderr') and e.stderr:
    stderr_str = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr
    output += f"--- STDERR (parcial) ---\n{stderr_str}\n"
return output
```

También teníamos el problema de que si el código genera un bucle infinito, la salida de `test_mas_code` superaba el límite de _tokens_. Lo solucionamos limitando el tamaño de la salida a unos 10000 caracteres, que debería producir salidas por debajo del limite de 130000 tokens del modelo.

Otra _tool_ importante es `exit_loop`, ya que, si no funciona, el desarrollo nunca termina satisfactoriamente. Para que los agentes funcionen en bucle hemos usado un `LoopAgent` llamado _refiner_, pero los `LoopAgent`, #link("https://adk.dev/agents/workflow-agents/loop-agents/")[de acuerdo a la documentación de `adk`], no pueden elegir cuando finalizar. `exit_loop` finaliza el código sobreescribiendo el valor de dos parámetros:

```python
def exit_loop(tool_context: ToolContext):
    # ...
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    # ...
```

Por otro lado, para la _tool_ `search_local_docs`, hemos eliminado documentos que considerabamos irrelevantes o incluso nocivos para la generación del JASON (por ejemplo, uno de los documentos del proyecto base era casi todo código Java que confundía al agente de IA) y en su lugar hemos añadido extractos relevantes de _Programming Multi-Agent Systems in AgentSpeak using Jason_.

Por último, la _tool_ `search_github_examples` también se ha modificado para eliminar del principio del `path` el contenido de `category`, pues a menudo el modelo de IA se confunde y vez de buscar `category="examples", path="lorem-ipsum"` acaba buscando `category="examples", path="examples/lorem-ipsum"`, que no daría resultado.

= Instrucciones

Hemos dividio las instrucciones (visibles en `agent/instructions`) en diferentes archivos.

Lo primero que hemos hecho, indicarles a los agentes relevantes (todos menos los _Searcher_) las reglas sintácticas y semánticas del lenguaje JASON en una _cheatsheet_, al principio de sus instrucciones. Hemos detectado que eso mejora mucho toda una clase de errores, en los que el código estaba mayoritariamente bien pero, por ejemplo, faltaban creencias iniciales o se usaban mal ciertos símbolos.

También les hemos indicado a todos los agentes que sean breves, porque por defecto son excesivamente verbosos y eso empeora los tiempos de respuesta sin mejorar significativamente la calidad de las mismas.

De especial importancia ha sido también aclarar al agente cómo funciona exactamente `search_github_examples`, ya que el agente, al no saber a qué ejemplos tenía acceso, malgastaba tiempo buscando ejemplos inexistentes o directamente finalizaba sin encontrar ejemplos.

= Referencias

Documentación de Google Adk: _#link("https://adk.dev/agents")_

Extractos de _Programming Multi-Agent Systems in AgentSpeak using Jason_, de Rafael H. Bordini y Jomi Fred Hübner.
