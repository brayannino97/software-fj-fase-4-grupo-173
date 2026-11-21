"""Software FJ: gestión de clientes, servicios y reservas en memoria."""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import logging
import re
from typing import Callable, overload, TypeVar

CENTAVO = Decimal("0.01")
T = TypeVar("T", bound="Entidad")


class ErrorFJ(Exception):
    """Error de negocio controlado y comprensible para el usuario."""


class DatoInvalido(ErrorFJ):
    """Identificador, valor o parámetro inválido."""


class OperacionNoPermitida(ErrorFJ):
    """Operación incompatible con las reglas o el estado actual."""


class ServicioNoDisponible(ErrorFJ):
    """El servicio está inactivo o ya tiene una reserva incompatible."""


class CalculoInvalido(ErrorFJ):
    """Importe no representable o tasa inválida."""


def texto(valor: str, campo: str) -> str:
    """Normaliza una cadena requerida sin modificar su significado."""
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalido(f"{campo}: falta un texto válido")
    return valor.strip()


def numero(valor: object, campo: str, *, minimo: str, maximo: str) -> Decimal:
    """Convierte una entrada a decimal, conservando la causa si falla."""
    try:
        if isinstance(valor, bool):
            raise ValueError("un booleano no es un valor numérico válido")
        resultado = Decimal(str(valor))
        if not resultado.is_finite() or not Decimal(minimo) <= resultado <= Decimal(maximo):
            raise ValueError(f"se esperaba un valor entre {minimo} y {maximo}")
    except (InvalidOperation, TypeError, ValueError) as causa:
        raise DatoInvalido(f"{campo}: se esperaba un número entre {minimo} y {maximo}") from causa
    else:
        return resultado


class Entidad(ABC):
    """Contrato para clientes, servicios y reservas identificables."""

    def __init__(self, codigo: str) -> None:
        self.__codigo = texto(codigo, "Código").upper()

    @property
    def codigo(self) -> str:
        return self.__codigo

    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción sin datos de contacto."""


class Cliente(Entidad):
    """Cliente con datos personales encapsulados y validados."""

    def __init__(self, codigo: str, nombre: str, correo: str) -> None:
        super().__init__(codigo)
        self.__nombre = texto(nombre, "Nombre")
        contacto = texto(correo, "Correo").lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contacto):
            raise DatoInvalido("Correo: formato inválido")
        self.__correo = contacto

    @property
    def nombre(self) -> str:
        return self.__nombre

    @property
    def correo(self) -> str:
        return self.__correo

    def describir(self) -> str:
        return f"Cliente {self.codigo}"


class Servicio(Entidad, ABC):
    """Contrato de cálculo y validación común a todo el catálogo."""

    def __init__(self, codigo: str, nombre: str, tarifa: object) -> None:
        super().__init__(codigo)
        self.__nombre = texto(nombre, "Nombre del servicio")
        self.__tarifa = numero(tarifa, "Tarifa por hora", minimo="0.01", maximo="100000000")
        self.__disponible = True

    @property
    def tarifa(self) -> Decimal:
        return self.__tarifa

    @property
    def disponible(self) -> bool:
        return self.__disponible

    def cambiar_disponibilidad(self, disponible: bool) -> None:
        if type(disponible) is not bool:
            raise DatoInvalido("Disponibilidad: se esperaba un booleano")
        self.__disponible = disponible

    def _descripcion(self, tipo: str) -> str:
        return f"{tipo}: {self.__nombre} ({self.codigo}), {self.tarifa:,.2f} COP/h"

    @abstractmethod
    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        """Valida las opciones específicas y devuelve el importe base."""

    @overload
    def calcular_costo(self, duracion: object) -> Decimal: ...
    @overload
    def calcular_costo(self, duracion: object, *, impuesto: object = 0,
                      descuento: object = 0, **opciones: object) -> Decimal: ...

    def calcular_costo(self, duracion: object, *, impuesto: object = 0,
                      descuento: object = 0, **opciones: object) -> Decimal:
        """Admite cálculo simple y variantes con opciones, recargos y descuentos."""
        horas = numero(duracion, "Duración (horas)", minimo="0.25", maximo="24")
        base = self.validar_parametros(horas, opciones)
        try:
            tasa = numero(impuesto, "Impuesto (%)", minimo="0", maximo="100") / 100
            rebaja = numero(descuento, "Descuento (%)", minimo="0", maximo="100") / 100
            return (base * (1 - rebaja) * (1 + tasa)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        except (DatoInvalido, InvalidOperation) as causa:
            raise CalculoInvalido("No se pudo calcular el costo: revise impuesto y descuento") from causa

    @staticmethod
    def _opciones(opciones: dict[str, object], permitidas: set[str]) -> None:
        if opciones.keys() - permitidas:
            raise DatoInvalido("Se recibieron parámetros que no corresponden al servicio")


class Sala(Servicio):
    def describir(self) -> str:
        return self._descripcion("Reserva de sala")

    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        self._opciones(opciones, {"personas"})
        personas = opciones.get("personas", 1)
        if type(personas) is not int or not 1 <= personas <= 20:
            raise DatoInvalido("Sala: se admiten entre 1 y 20 personas")
        return horas * self.tarifa


class Equipo(Servicio):
    def describir(self) -> str:
        return self._descripcion("Alquiler de equipos")

    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        self._opciones(opciones, {"unidades"})
        unidades = opciones.get("unidades", 1)
        if type(unidades) is not int or not 1 <= unidades <= 10:
            raise DatoInvalido("Equipo: se admiten entre 1 y 10 unidades")
        return horas * self.tarifa * unidades


class Asesoria(Servicio):
    def describir(self) -> str:
        return self._descripcion("Asesoría especializada")

    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        self._opciones(opciones, {"modalidad"})
        modalidad = opciones.get("modalidad", "virtual")
        if modalidad not in ("virtual", "presencial"):
            raise DatoInvalido("Asesoría: modalidad virtual o presencial")
        if horas > 8:
            raise DatoInvalido("Asesoría: duración máxima de 8 horas")
        factor = Decimal("1.15") if modalidad == "presencial" else Decimal("1")
        return horas * self.tarifa * factor


class Estado(Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    PROCESADA = "procesada"


class Reserva(Entidad):
    """Conserva cliente, servicio, duración y transiciones válidas de estado."""

    def __init__(self, codigo: str, cliente: Cliente, servicio: Servicio,
                 duracion: object, **opciones: object) -> None:
        super().__init__(codigo)
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise DatoInvalido("Reserva: se requiere un cliente y un servicio válidos")
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = numero(duracion, "Duración", minimo="0.25", maximo="24")
        self.__estado = Estado.PENDIENTE
        self.__total = servicio.calcular_costo(self.duracion, **opciones)

    @property
    def cliente(self) -> Cliente:
        return self.__cliente

    @property
    def servicio(self) -> Servicio:
        return self.__servicio

    @property
    def duracion(self) -> Decimal:
        return self.__duracion

    @property
    def estado(self) -> Estado:
        return self.__estado

    @property
    def total(self) -> Decimal:
        return self.__total

    def describir(self) -> str:
        return (f"{self.codigo} | {self.cliente.codigo}/{self.servicio.codigo} | "
                f"{self.duracion} h | {self.estado.value} | {self.total:,.2f} COP")

    def confirmar(self, ocupada: bool) -> None:
        if self.estado is not Estado.PENDIENTE:
            raise OperacionNoPermitida("Solo se puede confirmar una reserva pendiente")
        if ocupada or not self.servicio.disponible:
            raise ServicioNoDisponible("El servicio está ocupado o inactivo")
        self.__estado = Estado.CONFIRMADA

    def cancelar(self) -> None:
        if self.estado not in (Estado.PENDIENTE, Estado.CONFIRMADA):
            raise OperacionNoPermitida("Solo se puede cancelar una reserva pendiente o confirmada")
        self.__estado = Estado.CANCELADA

    def procesar(self) -> None:
        if self.estado is not Estado.CONFIRMADA:
            raise OperacionNoPermitida("Solo se puede procesar una reserva confirmada")
        if not self.servicio.disponible:
            raise ServicioNoDisponible("El servicio no está activo para completar la reserva")
        self.__estado = Estado.PROCESADA


class SistemaFJ:
    """Administra listas en memoria; una reserva confirmada ocupa el servicio."""

    def __init__(self) -> None:
        self.__clientes: list[Cliente] = []
        self.__servicios: list[Servicio] = []
        self.__reservas: list[Reserva] = []

    @staticmethod
    def _buscar(elementos: list[T], codigo: str) -> T:
        clave = texto(codigo, "Código").upper()
        for elemento in elementos:
            if elemento.codigo == clave:
                return elemento
        raise DatoInvalido("Código no encontrado")

    @staticmethod
    def _agregar(elementos: list[T], nuevo: T) -> T:
        if any(elemento.codigo == nuevo.codigo for elemento in elementos):
            raise OperacionNoPermitida("Ya existe un elemento con ese código")
        elementos.append(nuevo)
        return nuevo

    def registrar_cliente(self, codigo: str, nombre: str, correo: str) -> Cliente:
        return self._agregar(self.__clientes, Cliente(codigo, nombre, correo))

    def crear_servicio(self, tipo: str, codigo: str, nombre: str, tarifa: object) -> Servicio:
        clases = {"sala": Sala, "equipo": Equipo, "asesoria": Asesoria}
        try:
            clase = clases[texto(tipo, "Tipo de servicio").lower()]
        except KeyError as causa:
            raise DatoInvalido("Tipo de servicio desconocido") from causa
        return self._agregar(self.__servicios, clase(codigo, nombre, tarifa))

    def consultar_servicio(self, codigo: str) -> Servicio:
        return self._buscar(self.__servicios, codigo)

    def _ocupado(self, servicio: Servicio) -> bool:
        return any(r.servicio is servicio and r.estado is Estado.CONFIRMADA for r in self.__reservas)

    def reservar(self, codigo: str, cod_cliente: str, cod_servicio: str,
                 duracion: object, **opciones: object) -> Reserva:
        cliente = self._buscar(self.__clientes, cod_cliente)
        servicio = self._buscar(self.__servicios, cod_servicio)
        if not servicio.disponible or self._ocupado(servicio):
            raise ServicioNoDisponible("El servicio está ocupado o inactivo")
        return self._agregar(self.__reservas, Reserva(codigo, cliente, servicio, duracion, **opciones))

    def confirmar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.confirmar(self._ocupado(reserva.servicio))
        return reserva

    def cancelar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.cancelar()
        return reserva

    def procesar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.procesar()
        return reserva

    def cambiar_disponibilidad(self, codigo: str, disponible: bool) -> Servicio:
        servicio = self._buscar(self.__servicios, codigo)
        servicio.cambiar_disponibilidad(disponible)
        return servicio


def configurar_log(ruta: str = "software_fj.log") -> logging.Logger:
    """Registra solo operaciones, estados y errores; no guarda datos de clientes."""
    registro = logging.getLogger("software_fj")
    registro.setLevel(logging.INFO)
    registro.propagate = False
    for anterior in tuple(registro.handlers):
        registro.removeHandler(anterior)
        anterior.close()
    salida = logging.FileHandler(ruta, encoding="utf-8")
    salida.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    registro.addHandler(salida)
    return registro


def ejecutar(registro: logging.Logger, descripcion: str, accion: Callable[[], object]) -> object:
    """Aísla cada operación y registra el cierre, incluso después de un error."""
    registro.info("Inicio: %s", descripcion)
    try:
        resultado = accion()
    except ErrorFJ as error:
        registro.error("%s: %s (%s)", descripcion, error, type(error).__name__)
        causa = error.__cause__
        while causa is not None:
            # No se escribe el valor original ingresado en la bitácora.
            registro.info("Causa técnica: %s", type(causa).__name__)
            causa = causa.__cause__
        raise
    else:
        registro.info("Éxito: %s", descripcion)
        return resultado
    finally:
        registro.info("Cierre: %s", descripcion)
