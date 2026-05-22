# ¿Qué es esto?

Lo usamos para apuntar los problemas que vamos teniendo con el agente, para saber qué hacer luego en la memoria.

# Arquitectura multiagente

La estructura del sistema multiagente, viendo sólo las hojas del árbol, es algo así:

```
   ╭── Web_Searcher ──╮
╭──┤                  ├── Coder ─── Tester ──┬── End
│  ╰── Doc_Searcher ──╯                      │
│                                            │
╰────────────────────────────────────────────╯
```

# PROBLEMAS

## El agente no usa o no sabe usar `search_github_examples`

`search_github_examples` no funciona correctamente. Tenemos dos opciones:
- Tratar de enseñar a la IA como funciona.
- Reescribirlo para que sea más fácil de utilizar y usar agentes en secuencia.

### Solución

Parte de la solución radica en que ahora Web_Searcher se encarga en exclusiva de usar `search_github_examples`.

También se ha enseñado a este agente como debe usarlo, principalmente:
- Siendo más explícitos con qué parámetro sirve para qué.
- Especificando los posibles valores del parámetro `category`.

Finalmente, como el modelo de IA pone el contenido de `category` también al principio de `path`, se ha modificado `search_github_examples` para eliminar esa parte del `path`.

```python
path = re.sub(rf"^{category}\/", "", path)
```

## El agente se olvida de poner la creencia inicial

El agente no pone la creencia inicial que hace que inicie el programa (ej. `!start.`).

### Solución

Aclarar como funciona JASON y arreglar algunas confusiones con la terminología en las instrucciones arregla mayoritariamente el problema.

Con eso y arreglando `test_mas_code`, el problema ha (prácticamente) desaparecido.

## Confusiones con los símbolos

El agente de IA se equivoca muy a menudo con qué símbolos se usan para qué cosas. He aquí una lista de ejemplos:

- La concatenación debe usar comas `,`, pero a menudo pone `+`.
  - Correcto: `.print("Fib(", Cnt, ") = ", A);`
  - Incorrecto: `.print("Fib(" + Cnt + ") = " + A);`

- Los elementos del cuerpo de un plan deben ir separados por `;`, pero pone `,`.
  - Correcto: `.print(A); !fib_seq(Cnt + 1, B, A + B).`
  - Incorrecto: `.print(A), !fib_seq(Cnt + 1, B, A + B).`

### Solución

Añadir la cheatsheet directamente en las instrucciones y arreglar `test_mas_code` para que también muestre `stderr`.

## La salida de `search_local_docs` se corta demasiado pronto

`search_local_docs` corta su salida tan pronto que no llega a alcanzar apenas contenido relevante.

## `test_mas_code` siempre falla con timeout.

Aunque el código funcione, `test_mas_code` siempre falla con timeout.

Cuando el código no funciona por un error sintáctico debería mostrar dónde está el error sintáctico, pero en su lugar falla por timeout.

### Solución

Se ha añadido el siguiente extracto de código a `test_mas_code`, dentro del `except subprocess.TimeoutExpired` para mostrar el error estándar en vez de sólamente la salida estándar.

```python
if hasattr(e, 'stderr') and e.stderr:
    stderr_str = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr
    output += f"--- STDERR (parcial) ---\n{stderr_str}\n"
```

Resulta que tanto la salida de los errores como la salida de los agentes funcionales van por `stderr`.

## Los bucles infinitos superan el máximo de tokens

Cuando el agente genera sin querer un bucle infinito en el que muestra salida, puede superar el máximo de tokens del modelo y hacer que todo se rompa.

### Solución

Lo solucionamos limitando el tamaño de la salida a unos 10000 caracteres, que debería producir salidas por debajo del limite de 130000 tokens del modelo.

## El sistema multiagente siempre repite el proceso de desarrollo

Aunque el resultado generado devuelva código válido que hace lo que pide el usuario, vuelven a iterar desde el principio.

### Solución

La solución consiste en añadir una tool al agente Tester que detenga la ejecución del bucle, tal y como se describe en la documentación del `LoopAgent`.

```python
def exit_loop(tool_context: ToolContext):
    # ...
    tool_context.actions.escalate = True
    tool_context.actions.skip_summarization = True
    # ...
```

La tool es una función que recibe un `tool_context` que permite modificar el estado de la _pipeline_ de forma que el LoopAgent delegue sobre su padre, el `root_agent`, que pasará a ejecutar el agente `saver`

Obviamente, también se ha tenido que enseñar al agente Tester cuándo debe usar esta tool.

## El agente tarda mucho en responder

Parte del problema parece ser que las respuestas se alargan excesivamente.

Se ha intentado poner en las instrucciones de cada agente que tanto sus pensamientos como respuestas deben ser breves, pero sólo funciona al principio.

## El agente saver nunca recibe código

Al asignar tool_context.actions.escalate = True, la librería google.adk entiende que ha ocurrido un evento crítico (o una señal de parada total) y aborta la ejecución de todo el árbol de agentes hacia arriba.

Esto significa que refiner se detiene, pero en lugar de pasar el testigo al siguiente agente de la lista en el SequentialAgent (saver), el pipeline principal finaliza por completo. El agente Saver nunca llega a recibir su turno de ejecución, y por ende, jamás lee su archivo saver.md ni invoca a save_mas_code.

### Solución

Lo que hemos hecho ha sido que el propio agente tester sea el encargado de guardar el código, por lo que saver ya no es necesario.