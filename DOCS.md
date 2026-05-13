# ¿Qué es esto?

Lo usamos para apuntar los problemas que vamos teniendo con el agente, para saber qué hacer luego en la memoria.

# PROBLEMAS

## El agente no usa o no sabe usar `search_github_examples`

`search_github_examples` no funciona correctamente. Tenemos dos opciones:
- Tratar de enseñar a la IA como funciona.
- Reescribirlo para que sea más fácil de utilizar y usar agentes en secuencia.

## El agente se olvida de poner la creencia inicial

El agente no pone la creencia inicial que hace que inicie el programa (ej. `!start.`).

## La tool `test_mas_code` no funciona prácticamente nunca

No falla necesariamente, pero da timeout y el agente de IA se ralla.

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
