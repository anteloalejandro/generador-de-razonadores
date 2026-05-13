fib_list([0,1,1,2,3,5,8,13,21,34]).

!start.

// Plan inicial que obtiene la lista e inicia la impresión
+!start <- ?fib_list(L); !print_sequence(L).

// Caso base: lista vacía, terminamos
+!print_sequence([]) <- .print("--- Fin de la secuencia Fibonacci ---").

// Caso recursivo: imprime el primer elemento y continúa con el resto
+!print_sequence([H|T]) <- .print(H); !print_sequence(T).