"""Interfaz de consola y simulaciones ejecutables para Software FJ."""
# Lee las opciones de ejecución que se pasan desde la terminal.
import argparse
# Permite cerrar y vaciar la bitácora al terminar el programa.
import logging
# Compara los importes esperados sin errores de redondeo binario.
from decimal import Decimal
# Importa el modelo, los tipos de servicio y las funciones de bitácora.
from software_fj import (
    SistemaFJ, ErrorFJ, DatoInvalido, OperacionNoPermitida, ServicioNoDisponible,
    Sala, Equipo, Asesoria,
    CalculoInvalido, Estado, configurar_log, ejecutar,
)


def demostrar(registro):
    """Ejecuta operaciones consecutivas y verifica errores, costos y estados."""
    # Crea una instancia vacía para que la demostración sea reproducible.
    app = SistemaFJ()
    # Cada caso lleva una etiqueta, una operación diferida y el error esperado, si lo hay.
    casos = [
        # Registra el cliente que será reutilizado en las reservas posteriores.
        ("Cliente válido", lambda: app.registrar_cliente("C01", "Ana Ejemplo", "ana@example.com"), None),
        # Comprueba que no se acepte un correo sin arroba.
        ("Correo inválido", lambda: app.registrar_cliente("C02", "Juan Ejemplo", "sin-arroba"), DatoInvalido),
        # Verifica que las minúsculas no permitan registrar un código repetido.
        ("Cliente duplicado", lambda: app.registrar_cliente("c01", "Luis Ejemplo", "luis@example.com"), OperacionNoPermitida),
        # Crea la sala que se usará en los escenarios de costo y ocupación.
        ("Servicio tipo sala", lambda: app.crear_servicio("sala", "S01", "Principal", 50000), None),
        # Prueba que un tipo fuera del catálogo sea rechazado.
        ("Tipo de servicio no reconocido", lambda: app.crear_servicio("otro", "S00", "Prueba", 10000), DatoInvalido),
        # Comprueba que una tarifa negativa no llegue al catálogo.
        ("Equipo con tarifa inválida", lambda: app.crear_servicio("equipo", "S02", "Proyector", -5), DatoInvalido),
        # Reutiliza el código del equipo porque el intento anterior no lo guardó.
        ("Servicio tipo equipo", lambda: app.crear_servicio("equipo", "S02", "Proyector", 20000), None),
        # Agrega la asesoría para probar el recargo presencial.
        ("Servicio tipo asesoría", lambda: app.crear_servicio("asesoria", "S03", "Soporte", 80000), None),
        # Prueba la validación de un código de cliente vacío.
        ("Reserva con código de cliente faltante", lambda: app.reservar("R00", "", "S01", 2), DatoInvalido),
        # Comprueba el límite inferior de duración.
        ("Reserva con duración inválida", lambda: app.reservar("R00", "C01", "S01", 0), DatoInvalido),
        # Combina descuento e impuesto en una reserva válida.
        ("Reserva de sala con impuesto y descuento", lambda: app.reservar("R01", "C01", "S01", 2, personas=7, impuesto=19, descuento=10), None),
        # Confirma la reserva para que la sala quede ocupada en el siguiente caso.
        ("Confirmación de sala", lambda: app.confirmar("R01"), None),
        # Verifica que no se pueda reservar la sala mientras está ocupada.
        ("Reserva sobre servicio ocupado", lambda: app.reservar("R02", "C01", "S01", 1), ServicioNoDisponible),
        # Procesa la reserva confirmada.
        ("Procesamiento de sala", lambda: app.procesar("R01"), None),
        # Comprueba que un estado procesado no permite cancelar.
        ("Cancelación de reserva procesada", lambda: app.cancelar("R01"), OperacionNoPermitida),
        # Usa un impuesto no numérico para probar la excepción de cálculo.
        ("Reserva de equipo con impuesto inconsistente", lambda: app.reservar("R02", "C01", "S02", 1, impuesto="abc"), CalculoInvalido),
        # Desactiva el equipo para separar indisponibilidad de ocupación.
        ("Equipo desactivado", lambda: app.cambiar_disponibilidad("S02", False), None),
        # Comprueba que no se reserve un equipo inactivo.
        ("Reserva de equipo inactivo", lambda: app.reservar("R02", "C01", "S02", 1), ServicioNoDisponible),
        # Reactiva el equipo para el caso de múltiples unidades.
        ("Equipo reactivado", lambda: app.cambiar_disponibilidad("S02", True), None),
        # Prueba una duración fraccionaria con dos unidades.
        ("Reserva de dos unidades de equipo", lambda: app.reservar("R02", "C01", "S02", 1.5, unidades=2), None),
        # Verifica que una reserva pendiente pueda cancelarse.
        ("Cancelación de equipo", lambda: app.cancelar("R02"), None),
        # Comprueba el recargo de la modalidad presencial.
        ("Reserva de asesoría presencial", lambda: app.reservar("R03", "C01", "S03", 1, modalidad="presencial"), None),
        # Confirma que la asesoría puede pasar al estado confirmado.
        ("Confirmación de asesoría", lambda: app.confirmar("R03"), None),
    ]
    # Asocia a cada caso monetario el total exacto que se debe obtener.
    costos = {11: Decimal("107100.00"), 20: Decimal("60000.00"), 22: Decimal("92000.00")}
    # Define las transiciones de estado que la simulación debe comprobar.
    estados = {12: Estado.CONFIRMADA, 14: Estado.PROCESADA,
               21: Estado.CANCELADA, 23: Estado.CONFIRMADA}
    # Identifica los casos en los que también debe conservarse la causa técnica.
    con_causa = {5: KeyError, 6: ValueError, 10: ValueError, 16: DatoInvalido}
    # Cuenta únicamente los casos que coincidan con lo esperado.
    total = 0
    # Numera los escenarios en el mismo orden de las expectativas.
    for n, (etiqueta, operacion, esperado) in enumerate(casos, 1):
        try:
            # Envuelve cada operación con el registro de inicio, resultado y cierre.
            resultado = ejecutar(registro, etiqueta, operacion)
        except ErrorFJ as error:
            # Exige el tipo exacto de error previsto para este caso.
            ok = type(error) is esperado
            # Comprueba la causa original solamente donde se definió una.
            if n in con_causa:
                ok = ok and isinstance(error.__cause__, con_causa[n])
            # Muestra un diagnóstico identificable sin detener la simulación.
            detalle = f"{type(error).__name__}: {error}"
        else:
            # Una operación exitosa solo es correcta si no se esperaba una excepción.
            ok = esperado is None
            if n in costos:
                # Verifica el importe de los escenarios monetarios.
                ok = ok and resultado.total == costos[n]
            if n in estados:
                # Compara el estado final con el valor del enumerado previsto.
                ok = ok and resultado.estado is estados[n]
            # Resume el resultado con la descripción que proporciona el objeto.
            detalle = resultado.describir()
        # Emite una línea de evidencia con el veredicto de cada caso.
        print(f"{n:02} [{'OK' if ok else 'FALLÓ'}] {etiqueta}: {detalle}")
        # Convierte el acierto en uno y el fallo en cero para acumular.
        total += int(ok)
    # Informa cuántos escenarios superaron la verificación.
    print(f"\nResultado: {total}/{len(casos)} casos con el resultado esperado.")
    # La demostración solo aprueba si todos los casos coinciden.
    return total == len(casos)


def menu(registro):
    """Captura entradas y conserva el menú activo frente a errores esperados."""
    # Conserva los datos en memoria mientras dura la sesión interactiva.
    app = SistemaFJ()
    # Los índices de estas etiquetas coinciden con los números del menú.
    opciones = (
        "Salir", "Registrar cliente", "Crear servicio", "Crear reserva",
        "Confirmar reserva", "Cancelar reserva", "Procesar reserva",
        "Cambiar disponibilidad",
    )

    # Centraliza la lectura y elimina espacios accidentales en los extremos.
    def pedir(mensaje):
        return input(mensaje + ": ").strip()

    # Interpreta una respuesta corta y la traduce al valor lógico del servicio.
    def disponibilidad():
        codigo = pedir("Código del servicio")
        estado = pedir("¿Disponible? (s/n)").lower()
        # Rechaza valores distintos de sí o no antes de cambiar el estado.
        if estado not in ("s", "n"):
            raise DatoInvalido("Responda con s o n")
        # Actualiza la disponibilidad y devuelve el servicio actualizado.
        servicio = app.cambiar_disponibilidad(codigo, estado == "s")
        print(f"Disponible: {'sí' if servicio.disponible else 'no'}")
        return servicio

    # Recoge los datos comunes de la reserva y las opciones de su servicio.
    def reservar():
        codigo = pedir("Código de reserva")
        cliente = pedir("Código de cliente")
        servicio = pedir("Código de servicio")
        horas = pedir("Duración en horas (punto decimal)")
        # Identifica la clase concreta para preguntar solo por los datos pertinentes.
        servicio_elegido = app.consultar_servicio(servicio)
        # Reúne las opciones específicas que se enviarán a la reserva.
        extras = {}
        # Para sala se pide el aforo; el valor omitido equivale a una persona.
        if isinstance(servicio_elegido, Sala):
            extras["personas"] = entero_opcional("Número de personas (predeterminado: 1)")
        # Para equipo se pide el número de unidades.
        elif isinstance(servicio_elegido, Equipo):
            extras["unidades"] = entero_opcional("Unidades (predeterminado: 1)")
        # Para asesoría se usa modalidad virtual cuando la entrada queda vacía.
        elif isinstance(servicio_elegido, Asesoria):
            extras["modalidad"] = pedir("Modalidad virtual/presencial (predeterminado: virtual)").lower() or "virtual"
        # Las tasas omitidas se envían como cero para mantener el costo base.
        impuesto = pedir("Impuesto en %, opcional") or 0
        descuento = pedir("Descuento en %, opcional") or 0
        # Delega cálculos y validaciones a la capa de negocio.
        return app.reservar(codigo, cliente, servicio, horas, impuesto=impuesto, descuento=descuento, **extras)

    # Convierte cantidades opcionales a enteros sin ocultar la causa de un error.
    def entero_opcional(mensaje):
        try:
            # Usa una unidad como valor predeterminado al dejar el campo vacío.
            return int(pedir(mensaje) or "1")
        except ValueError as causa:
            # Presenta un mensaje comprensible y conserva el error de conversión.
            raise DatoInvalido("La cantidad debe ser un número entero") from causa

    # Relaciona cada número con la acción que se ejecutará al seleccionarlo.
    acciones = {
        "1": lambda: app.registrar_cliente(pedir("Código"), pedir("Nombre"), pedir("Correo")),
        "2": lambda: app.crear_servicio(pedir("Tipo (sala/equipo/asesoria)"),
                                         pedir("Código"), pedir("Nombre"),
                                         pedir("Tarifa por hora en COP")),
        "3": reservar,
        "4": lambda: app.confirmar(pedir("Código de reserva")),
        "5": lambda: app.cancelar(pedir("Código de reserva")),
        "6": lambda: app.procesar(pedir("Código de reserva")),
        "7": disponibilidad,
    }
    # Identifica la aplicación antes de mostrar las opciones.
    print("Software FJ | Gestión de clientes, servicios y reservas")
    # Mantiene el menú activo después de cada operación.
    while True:
        # Genera la lista numerada a partir de las etiquetas, incluida la salida.
        print("\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(opciones)))
        try:
            seleccion = pedir("Opción")
            # El cero cierra la sesión sin ejecutar una operación de negocio.
            if seleccion == "0":
                return
            # Registra una opción inválida y vuelve al inicio del menú.
            if seleccion not in acciones:
                registro.error("Opción de menú inválida")
                print("Elija una opción del menú.")
                continue
            # Ejecuta la opción válida usando la misma bitácora de la demostración.
            resultado = ejecutar(registro, opciones[int(seleccion)], acciones[seleccion])
        # Muestra el error de negocio sin cerrar la sesión.
        except ErrorFJ as error:
            print(f"No se completó la operación: {error}")
        # Permite cerrar de forma limpia si se interrumpe la entrada.
        except (EOFError, KeyboardInterrupt):
            print("\nSesión finalizada.")
            return
        # Presenta el resultado solo si se completó la operación.
        else:
            print(resultado.describir())


# Selecciona entre la demostración y el menú desde la línea de comandos.
def main():
    parser = argparse.ArgumentParser(description="Software FJ")
    # Activa la demostración sin requerir datos interactivos.
    parser.add_argument("--demo", action="store_true", help="ejecuta 23 casos reproducibles")
    # Acepta una ruta alternativa para la bitácora.
    parser.add_argument("--log", default="software_fj.log", help="ruta de la bitácora")
    # Valida los argumentos recibidos antes de configurar el registro.
    args = parser.parse_args()
    try:
        # Abre la bitácora antes de ejecutar cualquier operación.
        registro = configurar_log(args.log)
    # Si no se puede escribir el registro, termina con un código distinto de éxito.
    except OSError:
        print("No se pudo abrir la bitácora. Indique una ruta con permiso de escritura en --log.")
        return 2
    try:
        # Devuelve cero si todos los escenarios pasan y uno si algún caso falla.
        if args.demo:
            return 0 if demostrar(registro) else 1
        # Abre el flujo interactivo cuando no se pidió la demostración.
        menu(registro)
        return 0
    # Cierra los recursos de logging tanto en el flujo normal como ante errores.
    finally:
        logging.shutdown()


# Evita iniciar la aplicación al importar el módulo para reutilizarlo.
if __name__ == "__main__":
    raise SystemExit(main())
