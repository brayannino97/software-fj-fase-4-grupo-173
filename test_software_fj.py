from decimal import Decimal
import unittest

from software_fj import Estado, SistemaFJ, DatoInvalido, CalculoInvalido
from software_fj import Entidad, Servicio, OperacionNoPermitida, ServicioNoDisponible


class PruebasSoftwareFJ(unittest.TestCase):
    def setUp(self):
        self.app = SistemaFJ()
        self.app.registrar_cliente("C01", "Cliente de prueba", "cliente@example.com")
        self.sala = self.app.crear_servicio("sala", "S01", "Principal", 50000)

    def test_abstractas(self):
        for clase, argumentos in [(Entidad, ("X",)), (Servicio, ("S", "Servicio", 1))]:
            with self.subTest(clase=clase.__name__), self.assertRaises(TypeError):
                clase(*argumentos)

    def test_normaliza_codigos_y_rechaza_duplicados(self):
        with self.assertRaises(OperacionNoPermitida):
            self.app.registrar_cliente(" c01 ", "Otro", "otro@example.com")
        self.assertIs(self.app.consultar_servicio(" s01 "), self.sala)

    def test_calculo_simple_y_combinado(self):
        self.assertEqual(self.sala.calcular_costo(2), Decimal("100000.00"))
        self.assertEqual(self.sala.calcular_costo(2, impuesto=19, descuento=10), Decimal("107100.00"))

    def test_encadenamiento_del_impuesto(self):
        with self.assertRaises(CalculoInvalido) as fallo:
            self.sala.calcular_costo(2, impuesto="invalido")
        self.assertIsInstance(fallo.exception.__cause__, DatoInvalido)

    def test_polimorfismo(self):
        equipo = self.app.crear_servicio("equipo", "S02", "Proyector", 20000)
        asesoria = self.app.crear_servicio("asesoria", "S03", "Soporte", 80000)
        self.assertEqual(equipo.calcular_costo(1.5, unidades=2), Decimal("60000.00"))
        self.assertEqual(asesoria.calcular_costo(1, modalidad="presencial"), Decimal("92000.00"))
        with self.assertRaises(DatoInvalido):
            self.sala.calcular_costo(2, personas=50)

    def test_confirmacion_bloquea_y_cancelacion_libera(self):
        self.app.reservar("R01", "C01", "S01", 1)
        self.app.reservar("R02", "C01", "S01", 2)
        self.assertIs(self.app.confirmar("R01").estado, Estado.CONFIRMADA)
        with self.assertRaises(ServicioNoDisponible):
            self.app.confirmar("R02")
        self.assertIs(self.app.cancelar("R01").estado, Estado.CANCELADA)
        self.assertIs(self.app.confirmar("R02").estado, Estado.CONFIRMADA)
        self.assertIs(self.app.procesar("R02").estado, Estado.PROCESADA)
        with self.assertRaises(OperacionNoPermitida):
            self.app.cancelar("R02")

    def test_no_agrega_reserva_invalida(self):
        with self.assertRaises(DatoInvalido):
            self.app.reservar("R01", "C01", "S01", 0)
        self.assertIs(self.app.reservar("R01", "C01", "S01", 1).estado, Estado.PENDIENTE)


if __name__ == "__main__":
    unittest.main()
