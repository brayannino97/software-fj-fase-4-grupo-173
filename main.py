"""Interfaz de consola y simulaciones ejecutables para Software FJ."""
import argparse
import logging
from decimal import Decimal
from software_fj import (
    SistemaFJ, ErrorFJ, DatoInvalido, OperacionNoPermitida, ServicioNoDisponible,
    Sala, Equipo, Asesoria,
    CalculoInvalido, Estado, configurar_log, ejecutar,
)


def demostrar(registro):
    """Ejecuta operaciones consecutivas y verifica errores, costos y estados."""
    app = SistemaFJ()
    casos = [
        ("Cliente válido", lambda: app.registrar_cliente("C01", "Ana Ejemplo", "ana@example.com"), None),
        ("Correo inválido", lambda: app.registrar_cliente("C02", "Juan Ejemplo", "sin-arroba"), DatoInvalido),
        ("Cliente duplicado", lambda: app.registrar_cliente("c01", "Luis Ejemplo", "luis@example.com"), OperacionNoPermitida),
        ("Servicio tipo sala", lambda: app.crear_servicio("sala", "S01", "Principal", 50000), None),
        ("Tipo de servicio no reconocido", lambda: app.crear_servicio("otro", "S00", "Prueba", 10000), DatoInvalido),
        ("Equipo con tarifa inválida", lambda: app.crear_servicio("equipo", "S02", "Proyector", -5), DatoInvalido),
        ("Servicio tipo equipo", lambda: app.crear_servicio("equipo", "S02", "Proyector", 20000), None),
        ("Servicio tipo asesoría", lambda: app.crear_servicio("asesoria", "S03", "Soporte", 80000), None),
        ("Reserva con código de cliente faltante", lambda: app.reservar("R00", "", "S01", 2), DatoInvalido),
        ("Reserva con duración inválida", lambda: app.reservar("R00", "C01", "S01", 0), DatoInvalido),
        ("Reserva de sala con impuesto y descuento", lambda: app.reservar("R01", "C01", "S01", 2, personas=7, impuesto=19, descuento=10), None),
        ("Confirmación de sala", lambda: app.confirmar("R01"), None),
        ("Reserva sobre servicio ocupado", lambda: app.reservar("R02", "C01", "S01", 1), ServicioNoDisponible),
        ("Procesamiento de sala", lambda: app.procesar("R01"), None),
        ("Cancelación de reserva procesada", lambda: app.cancelar("R01"), OperacionNoPermitida),
        ("Reserva de equipo con impuesto inconsistente", lambda: app.reservar("R02", "C01", "S02", 1, impuesto="abc"), CalculoInvalido),
        ("Equipo desactivado", lambda: app.cambiar_disponibilidad("S02", False), None),
        ("Reserva de equipo inactivo", lambda: app.reservar("R02", "C01", "S02", 1), ServicioNoDisponible),
        ("Equipo reactivado", lambda: app.cambiar_disponibilidad("S02", True), None),
        ("Reserva de dos unidades de equipo", lambda: app.reservar("R02", "C01", "S02", 1.5, unidades=2), None),
        ("Cancelación de equipo", lambda: app.cancelar("R02"), None),
        ("Reserva de asesoría presencial", lambda: app.reservar("R03", "C01", "S03", 1, modalidad="presencial"), None),
        ("Confirmación de asesoría", lambda: app.confirmar("R03"), None),
    ]
    costos = {11: Decimal("107100.00"), 20: Decimal("60000.00"), 22: Decimal("92000.00")}
    estados = {12: Estado.CONFIRMADA, 14: Estado.PROCESADA,
               21: Estado.CANCELADA, 23: Estado.CONFIRMADA}
    con_causa = {5: KeyError, 6: ValueError, 10: ValueError, 16: DatoInvalido}
    total = 0
    for n, (etiqueta, operacion, esperado) in enumerate(casos, 1):
        try:
            resultado = ejecutar(registro, etiqueta, operacion)
        except ErrorFJ as error:
            ok = type(error) is esperado
            if n in con_causa:
                ok = ok and isinstance(error.__cause__, con_causa[n])
            detalle = f"{type(error).__name__}: {error}"
        else:
            ok = esperado is None
            if n in costos:
                ok = ok and resultado.total == costos[n]
            if n in estados:
                ok = ok and resultado.estado is estados[n]
            detalle = resultado.describir()
        print(f"{n:02} [{'OK' if ok else 'FALLÓ'}] {etiqueta}: {detalle}")
        total += int(ok)
    print(f"\nResultado: {total}/{len(casos)} casos con el resultado esperado.")
    return total == len(casos)


def menu(registro):
    """Captura entradas y conserva el menú activo frente a errores esperados."""
    app = SistemaFJ()
    opciones = (
        "Salir", "Registrar cliente", "Crear servicio", "Crear reserva",
        "Confirmar reserva", "Cancelar reserva", "Procesar reserva",
        "Cambiar disponibilidad",
    )

    def pedir(mensaje):
        return input(mensaje + ": ").strip()

    def disponibilidad():
        codigo = pedir("Código del servicio")
        estado = pedir("¿Disponible? (s/n)").lower()
        if estado not in ("s", "n"):
            raise DatoInvalido("Responda con s o n")
        servicio = app.cambiar_disponibilidad(codigo, estado == "s")
        print(f"Disponible: {'sí' if servicio.disponible else 'no'}")
        return servicio

    def reservar():
        codigo = pedir("Código de reserva")
        cliente = pedir("Código de cliente")
        servicio = pedir("Código de servicio")
        horas = pedir("Duración en horas (punto decimal)")
        servicio_elegido = app.consultar_servicio(servicio)
        extras = {}
        if isinstance(servicio_elegido, Sala):
            extras["personas"] = entero_opcional("Número de personas (predeterminado: 1)")
        elif isinstance(servicio_elegido, Equipo):
            extras["unidades"] = entero_opcional("Unidades (predeterminado: 1)")
        elif isinstance(servicio_elegido, Asesoria):
            extras["modalidad"] = pedir("Modalidad virtual/presencial (predeterminado: virtual)").lower() or "virtual"
        impuesto = pedir("Impuesto en %, opcional") or 0
        descuento = pedir("Descuento en %, opcional") or 0
        return app.reservar(codigo, cliente, servicio, horas, impuesto=impuesto, descuento=descuento, **extras)

    def entero_opcional(mensaje):
        try:
            return int(pedir(mensaje) or "1")
        except ValueError as causa:
            raise DatoInvalido("La cantidad debe ser un número entero") from causa

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
    print("Software FJ | Gestión de clientes, servicios y reservas")
    while True:
        print("\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(opciones)))
        try:
            seleccion = pedir("Opción")
            if seleccion == "0":
                return
            if seleccion not in acciones:
                registro.error("Opción de menú inválida")
                print("Elija una opción del menú.")
                continue
            resultado = ejecutar(registro, opciones[int(seleccion)], acciones[seleccion])
        except ErrorFJ as error:
            print(f"No se completó la operación: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nSesión finalizada.")
            return
        else:
            print(resultado.describir())


def main():
    parser = argparse.ArgumentParser(description="Software FJ")
    parser.add_argument("--demo", action="store_true", help="ejecuta 23 casos reproducibles")
    parser.add_argument("--log", default="software_fj.log", help="ruta de la bitácora")
    args = parser.parse_args()
    try:
        registro = configurar_log(args.log)
    except OSError:
        print("No se pudo abrir la bitácora. Indique una ruta con permiso de escritura en --log.")
        return 2
    try:
        if args.demo:
            return 0 if demostrar(registro) else 1
        menu(registro)
        return 0
    finally:
        logging.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
