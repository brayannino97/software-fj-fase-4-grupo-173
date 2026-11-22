# Usa decimales exactos para comparar los resultados monetarios.
from decimal import Decimal
# Utiliza el marco de pruebas de la biblioteca estándar de Python.
import unittest

# Importa el sistema, sus estados y las excepciones que se comprueban.
from software_fj import Estado, SistemaFJ, DatoInvalido, CalculoInvalido
from software_fj import Entidad, Servicio, OperacionNoPermitida, ServicioNoDisponible


# Agrupa las pruebas unitarias del catálogo, el cálculo y las reservas.
class PruebasSoftwareFJ(unittest.TestCase):
    # Crea un conjunto de datos nuevo antes de cada caso para que sean independientes.
    def setUp(self):
        # Reinicia el sistema en memoria sin reutilizar el estado de otra prueba.
        self.app = SistemaFJ()
        # Registra un cliente ficticio que se usará en las reservas.
        self.app.registrar_cliente("C01", "Cliente de prueba", "cliente@example.com")
        # Crea una sala con tarifa conocida para comprobar importes reproducibles.
        self.sala = self.app.crear_servicio("sala", "S01", "Principal", 50000)

    # Verifica que los contratos abstractos no se puedan instanciar directamente.
    def test_abstractas(self):
        # Prepara los argumentos que se intentarían pasar a cada clase abstracta.
        for clase, argumentos in [(Entidad, ("X",)), (Servicio, ("S", "Servicio", 1))]:
            # Identifica cada clase por separado y exige un error de tipo al instanciarla.
            with self.subTest(clase=clase.__name__), self.assertRaises(TypeError):
                clase(*argumentos)

    # Comprueba que espacios y minúsculas no eviten las reglas de identidad.
    def test_normaliza_codigos_y_rechaza_duplicados(self):
        # El identificador normalizado coincide con el cliente de la preparación.
        with self.assertRaises(OperacionNoPermitida):
            self.app.registrar_cliente(" c01 ", "Otro", "otro@example.com")
        # La búsqueda normalizada devuelve exactamente el objeto de sala inicial.
        self.assertIs(self.app.consultar_servicio(" s01 "), self.sala)

    # Compara el cálculo básico y el cálculo que combina dos tasas.
    def test_calculo_simple_y_combinado(self):
        # Dos horas a 50 000 COP dan 100 000 COP sin tasas.
        self.assertEqual(self.sala.calcular_costo(2), Decimal("100000.00"))
        # El diez por ciento de descuento seguido del impuesto deja 107 100 COP.
        self.assertEqual(self.sala.calcular_costo(2, impuesto=19, descuento=10), Decimal("107100.00"))

    # Comprueba que el fallo visible de cálculo conserve la causa.
    def test_encadenamiento_del_impuesto(self):
        # Captura la excepción de cálculo originada por una tasa inválida.
        with self.assertRaises(CalculoInvalido) as fallo:
            self.sala.calcular_costo(2, impuesto="invalido")
        # Exige que la causa conservada sea la validación del dato de entrada.
        self.assertIsInstance(fallo.exception.__cause__, DatoInvalido)

    # Prueba las reglas propias de equipo, asesoría y sala.
    def test_polimorfismo(self):
        # Usa un equipo de 20 000 COP por hora para probar la cantidad de unidades.
        equipo = self.app.crear_servicio("equipo", "S02", "Proyector", 20000)
        # Usa una asesoría de 80 000 COP por hora para probar la modalidad presencial.
        asesoria = self.app.crear_servicio("asesoria", "S03", "Soporte", 80000)
        # Una hora y media de dos unidades debe dar 60 000 COP.
        self.assertEqual(equipo.calcular_costo(1.5, unidades=2), Decimal("60000.00"))
        # El recargo presencial del quince por ciento deja un total de 92 000 COP.
        self.assertEqual(asesoria.calcular_costo(1, modalidad="presencial"), Decimal("92000.00"))
        # Comprueba que el límite de aforo de la sala se respete.
        with self.assertRaises(DatoInvalido):
            self.sala.calcular_costo(2, personas=50)

    # Comprueba ocupación, liberación y transiciones de dos reservas de la misma sala.
    def test_confirmacion_bloquea_y_cancelacion_libera(self):
        # Crea la primera reserva sin ocupar todavía la sala.
        self.app.reservar("R01", "C01", "S01", 1)
        # Crea la segunda mientras las dos reservas siguen pendientes.
        self.app.reservar("R02", "C01", "S01", 2)
        # Confirma la primera para ocupar el servicio.
        self.assertIs(self.app.confirmar("R01").estado, Estado.CONFIRMADA)
        # La segunda no puede confirmarse mientras la sala no esté libre.
        with self.assertRaises(ServicioNoDisponible):
            self.app.confirmar("R02")
        # Cancela la primera para liberar el servicio.
        self.assertIs(self.app.cancelar("R01").estado, Estado.CANCELADA)
        # Verifica que la segunda se pueda confirmar después de la liberación.
        self.assertIs(self.app.confirmar("R02").estado, Estado.CONFIRMADA)
        # Una vez confirmada, comprueba que pueda pasar a procesada.
        self.assertIs(self.app.procesar("R02").estado, Estado.PROCESADA)
        # Verifica que una reserva procesada no vuelva al estado cancelado.
        with self.assertRaises(OperacionNoPermitida):
            self.app.cancelar("R02")

    # Comprueba que un fallo de validación no deje una reserva parcial.
    def test_no_agrega_reserva_invalida(self):
        # Fuerza un error de duración al intentar crear la reserva.
        with self.assertRaises(DatoInvalido):
            self.app.reservar("R01", "C01", "S01", 0)
        # El mismo código sigue disponible en el siguiente intento válido.
        self.assertIs(self.app.reservar("R01", "C01", "S01", 1).estado, Estado.PENDIENTE)


# Permite ejecutar las pruebas aunque se invoque directamente el archivo.
if __name__ == "__main__":
    unittest.main()
