# Software FJ

Sistema de gestión de clientes, servicios y reservas. Programación (213023), Fase 4. Grupo 213023_173. Universidad Nacional Abierta y a Distancia.

## Ejecución

Requiere Python 3.10 o superior. No requiere paquetes externos.

```sh
python main.py
python main.py --demo --log evidencia/bitacora_demo.log
python -m unittest discover -v
```

El primer comando abre el menú. El segundo ejecuta 23 casos de simulación y el tercero verifica las reglas de negocio con pruebas unitarias. El directorio `evidencia` existe en el paquete. La bitácora activa se escribe en modo de agregado; use otro nombre para separar ejecuciones.

## Organización

- `software_fj.py`: entidades, catálogo de servicios, reservas, excepciones y bitácora.
- `main.py`: menú y simulación verificable de 23 casos.
- `test_software_fj.py`: pruebas automatizadas de reglas de negocio.
- `evidencia/`: salida y bitácora de una ejecución real con datos ficticios.

## Reglas de la simulación

La información se mantiene en listas en memoria. No se usan bases de datos ni se guardan datos de clientes en la bitácora. Cada servicio tiene un código único y admite como máximo una reserva confirmada simultánea: no se modela una agenda con fechas. La cancelación o el procesamiento de la reserva libera el servicio. Las tarifas, capacidades y porcentajes de la demostración son parámetros ficticios, no políticas comerciales de Software FJ.

El importe usa aritmética decimal. Se calcula la base según el tipo de servicio, se aplica el descuento sobre la base, se calcula el impuesto sobre el importe descontado y se redondea al centavo. `calcular_costo` ofrece una forma simple y otra con parámetros opcionales. `typing.overload` documenta las firmas, que comparten una implementación de Python.

La bitácora registra el inicio, el resultado y el cierre de cada operación, incluso si la validación falla. Si una excepción tiene causa técnica, registra su tipo sin copiar valores personales suministrados por el usuario.
