# ¿Qué es esto?

Lo usamos para apuntar los problemas que vamos teniendo con el agente, para saber qué hacer luego en la memoria.

# PROBLEMAS

## El agente no usa o no sabe usar search_github_examples

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
