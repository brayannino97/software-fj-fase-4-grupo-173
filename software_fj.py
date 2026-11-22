"""Software FJ: gestión de clientes, servicios y reservas en memoria."""
# Permite utilizar nombres de clases definidos más adelante en las anotaciones.
from __future__ import annotations

# Define contratos de clases abstractas e implementaciones obligatorias.
from abc import ABC, abstractmethod
# Realiza cálculos monetarios decimales y controla conversiones no válidas.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Representa estados mediante valores únicos del enumerado.
from enum import Enum
# Centraliza la creación de la bitácora de operaciones.
import logging
# Se utiliza para validar el formato básico del correo.
import re
# Expresa firmas alternativas y conserva el tipo concreto de las entidades genéricas.
from typing import Callable, overload, TypeVar

# Fija la precisión del total monetario en dos decimales.
CENTAVO = Decimal("0.01")
# Restringe el tipo usado por búsqueda y registro a objetos con código.
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
    # Impide usar entradas vacías o valores que no son cadenas.
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalido(f"{campo}: falta un texto válido")
    # Conserva el texto válido sin espacios al inicio ni al final.
    return valor.strip()


def numero(valor: object, campo: str, *, minimo: str, maximo: str) -> Decimal:
    """Convierte una entrada a decimal, conservando la causa si falla."""
    try:
        # Rechaza valores lógicos para no tratarlos como cantidades.
        if isinstance(valor, bool):
            raise ValueError("un booleano no es un valor numérico válido")
        # Convierte a partir del texto para evitar arrastrar artefactos binarios del float.
        resultado = Decimal(str(valor))
        # Excluye valores infinitos o no numéricos antes de aplicar los límites.
        if not resultado.is_finite() or not Decimal(minimo) <= resultado <= Decimal(maximo):
            raise ValueError(f"se esperaba un valor entre {minimo} y {maximo}")
    # Traduce los errores de formato y rango a una excepción de negocio con causa.
    except (InvalidOperation, TypeError, ValueError) as causa:
        raise DatoInvalido(f"{campo}: se esperaba un número entre {minimo} y {maximo}") from causa
    # Devuelve el decimal solo cuando completó todas las comprobaciones.
    else:
        return resultado


class Entidad(ABC):
    """Contrato para clientes, servicios y reservas identificables."""

    # Normaliza a mayúsculas para identificar el mismo código en búsquedas y altas.
    def __init__(self, codigo: str) -> None:
        self.__codigo = texto(codigo, "Código").upper()

    # La propiedad expone el identificador sin ofrecer un método público para cambiarlo.
    @property
    def codigo(self) -> str:
        return self.__codigo

    # Obliga a cada entidad concreta a definir su descripción.
    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción sin datos de contacto."""


class Cliente(Entidad):
    """Cliente con datos personales encapsulados y validados."""

    # Valida el nombre y el correo antes de guardar los datos del cliente.
    def __init__(self, codigo: str, nombre: str, correo: str) -> None:
        # Reutiliza la normalización de códigos definida por Entidad.
        super().__init__(codigo)
        self.__nombre = texto(nombre, "Nombre")
        # Guarda los correos con un formato uniforme en minúsculas.
        contacto = texto(correo, "Correo").lower()
        # Comprueba que haya partes válidas alrededor de la arroba y un dominio con punto.
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contacto):
            raise DatoInvalido("Correo: formato inválido")
        self.__correo = contacto

    # Expone el nombre con una propiedad de solo lectura.
    @property
    def nombre(self) -> str:
        return self.__nombre

    # Expone la dirección validada con una propiedad de solo lectura.
    @property
    def correo(self) -> str:
        return self.__correo

    # Evita mostrar el correo o nombre del cliente al describirlo en el menú.
    def describir(self) -> str:
        return f"Cliente {self.codigo}"


class Servicio(Entidad, ABC):
    """Contrato de cálculo y validación común a todo el catálogo."""

    # Inicializa los datos compartidos por todas las clases de servicio.
    def __init__(self, codigo: str, nombre: str, tarifa: object) -> None:
        super().__init__(codigo)
        self.__nombre = texto(nombre, "Nombre del servicio")
        # Valida que la tarifa en COP por hora sea positiva y esté dentro del límite.
        self.__tarifa = numero(tarifa, "Tarifa por hora", minimo="0.01", maximo="100000000")
        # Un servicio nuevo se puede reservar desde su creación.
        self.__disponible = True

    # La tarifa se consulta mediante una propiedad de solo lectura.
    @property
    def tarifa(self) -> Decimal:
        return self.__tarifa

    # La disponibilidad se consulta sin modificar directamente el atributo.
    @property
    def disponible(self) -> bool:
        return self.__disponible

    # Controla el cambio de disponibilidad a través de una operación validada.
    def cambiar_disponibilidad(self, disponible: bool) -> None:
        # Exige un booleano real en vez de aceptar números o textos equivalentes.
        if type(disponible) is not bool:
            raise DatoInvalido("Disponibilidad: se esperaba un booleano")
        self.__disponible = disponible

    # Unifica el formato de nombre, código y tarifa mostrado por cada subtipo.
    def _descripcion(self, tipo: str) -> str:
        return f"{tipo}: {self.__nombre} ({self.codigo}), {self.tarifa:,.2f} COP/h"

    # Cada servicio decide qué parámetros acepta y cómo obtiene el importe base.
    @abstractmethod
    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        """Valida las opciones específicas y devuelve el importe base."""

    # Declara la llamada mínima para el verificador de tipos; no ejecuta el cálculo.
    @overload
    def calcular_costo(self, duracion: object) -> Decimal: ...
    # Declara la firma con porcentajes y con opciones específicas del servicio.
    @overload
    def calcular_costo(self, duracion: object, *, impuesto: object = 0,
                      descuento: object = 0, **opciones: object) -> Decimal: ...

    def calcular_costo(self, duracion: object, *, impuesto: object = 0,
                      descuento: object = 0, **opciones: object) -> Decimal:
        """Admite cálculo simple y variantes con opciones, recargos y descuentos."""
        # Aplica los límites de duración comunes a todos los servicios.
        horas = numero(duracion, "Duración (horas)", minimo="0.25", maximo="24")
        # Delega el importe base al método concreto según el tipo de servicio.
        base = self.validar_parametros(horas, opciones)
        # Mantiene separado el error de parámetros del servicio del error de cálculo de tasas.
        try:
            # Convierte el impuesto de porcentaje a fracción.
            tasa = numero(impuesto, "Impuesto (%)", minimo="0", maximo="100") / 100
            # Convierte el descuento de porcentaje a fracción.
            rebaja = numero(descuento, "Descuento (%)", minimo="0", maximo="100") / 100
            # Aplica primero el descuento y luego el impuesto; redondea al centavo.
            return (base * (1 - rebaja) * (1 + tasa)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        # Conserva la causa técnica del fallo para registrarla sin revelar los datos de entrada.
        except (DatoInvalido, InvalidOperation) as causa:
            raise CalculoInvalido("No se pudo calcular el costo: revise impuesto y descuento") from causa

    # La validación del conjunto de opciones no necesita datos de una instancia.
    @staticmethod
    def _opciones(opciones: dict[str, object], permitidas: set[str]) -> None:
        # Detecta claves que el subtipo no reconoce antes de leer sus valores.
        if opciones.keys() - permitidas:
            raise DatoInvalido("Se recibieron parámetros que no corresponden al servicio")


# Modela el alquiler de un espacio con límite de personas.
class Sala(Servicio):
    # Etiqueta la descripción compartida como una reserva de sala.
    def describir(self) -> str:
        return self._descripcion("Reserva de sala")

    # Valida el aforo sin aumentar el costo por número de personas.
    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        # Solo permite el parámetro propio de una sala.
        self._opciones(opciones, {"personas"})
        # Supone una persona cuando el aforo no fue especificado.
        personas = opciones.get("personas", 1)
        # Acepta enteros de uno a veinte, sin tomar booleanos como cantidades.
        if type(personas) is not int or not 1 <= personas <= 20:
            raise DatoInvalido("Sala: se admiten entre 1 y 20 personas")
        # Calcula el importe base de sala con tarifa por hora.
        return horas * self.tarifa


# Modela alquileres donde la cantidad de equipos modifica el total.
class Equipo(Servicio):
    # Etiqueta la descripción como alquiler de equipos.
    def describir(self) -> str:
        return self._descripcion("Alquiler de equipos")

    # Valida cuántos equipos se solicitan antes de multiplicar el costo.
    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        # Rechaza opciones ajenas al tipo equipo.
        self._opciones(opciones, {"unidades"})
        # Considera un solo equipo si no se indica la cantidad.
        unidades = opciones.get("unidades", 1)
        # Limita la cantidad a enteros de uno a diez.
        if type(unidades) is not int or not 1 <= unidades <= 10:
            raise DatoInvalido("Equipo: se admiten entre 1 y 10 unidades")
        # Multiplica el costo por hora por la duración y el número de equipos.
        return horas * self.tarifa * unidades


# Modela las asesorías con costo dependiente de la modalidad.
class Asesoria(Servicio):
    # Etiqueta la descripción como asesoría especializada.
    def describir(self) -> str:
        return self._descripcion("Asesoría especializada")

    # Valida modalidad y duración antes de aplicar el posible recargo.
    def validar_parametros(self, horas: Decimal, opciones: dict[str, object]) -> Decimal:
        # Solo permite el parámetro modalidad para este tipo.
        self._opciones(opciones, {"modalidad"})
        # Usa la modalidad virtual como predeterminada.
        modalidad = opciones.get("modalidad", "virtual")
        # Impide tratar una modalidad desconocida como si fuera válida.
        if modalidad not in ("virtual", "presencial"):
            raise DatoInvalido("Asesoría: modalidad virtual o presencial")
        # La asesoría tiene un límite de horas más estricto que el general.
        if horas > 8:
            raise DatoInvalido("Asesoría: duración máxima de 8 horas")
        # La modalidad presencial aumenta el importe base en quince por ciento.
        factor = Decimal("1.15") if modalidad == "presencial" else Decimal("1")
        # Combina duración, tarifa y factor aplicable.
        return horas * self.tarifa * factor


# Define los cuatro estados permitidos de una reserva.
class Estado(Enum):
    # Estado inicial, antes de ocupar el servicio por confirmación.
    PENDIENTE = "pendiente"
    # La reserva ocupa el servicio mientras se mantiene confirmada.
    CONFIRMADA = "confirmada"
    # Una cancelación finaliza una reserva pendiente o confirmada.
    CANCELADA = "cancelada"
    # Una reserva procesada ya completó el servicio.
    PROCESADA = "procesada"


class Reserva(Entidad):
    """Conserva cliente, servicio, duración y transiciones válidas de estado."""

    # Asocia una reserva a entidades válidas y calcula el total al crearla.
    def __init__(self, codigo: str, cliente: Cliente, servicio: Servicio,
                 duracion: object, **opciones: object) -> None:
        # Aplica las mismas reglas de código de las demás entidades.
        super().__init__(codigo)
        # Impide crear reservas con referencias que no son objetos del modelo.
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise DatoInvalido("Reserva: se requiere un cliente y un servicio válidos")
        # Guarda las referencias al cliente y al servicio elegidos.
        self.__cliente = cliente
        self.__servicio = servicio
        # Conserva la duración validada como número decimal.
        self.__duracion = numero(duracion, "Duración", minimo="0.25", maximo="24")
        # La reserva no ocupa el servicio hasta ser confirmada.
        self.__estado = Estado.PENDIENTE
        # Utiliza la tarifa y las opciones del tipo de servicio seleccionado.
        self.__total = servicio.calcular_costo(self.duracion, **opciones)

    # Expone el cliente vinculado a la reserva.
    @property
    def cliente(self) -> Cliente:
        return self.__cliente

    # Expone el servicio que se usa para verificar disponibilidad.
    @property
    def servicio(self) -> Servicio:
        return self.__servicio

    # Expone la duración normalizada en horas.
    @property
    def duracion(self) -> Decimal:
        return self.__duracion

    # Expone el estado sin ofrecer un método público de asignación directa.
    @property
    def estado(self) -> Estado:
        return self.__estado

    # Expone el importe que se calculó al crear la reserva.
    @property
    def total(self) -> Decimal:
        return self.__total

    # Construye un resumen con identificadores, duración, estado y total.
    def describir(self) -> str:
        return (f"{self.codigo} | {self.cliente.codigo}/{self.servicio.codigo} | "
                f"{self.duracion} h | {self.estado.value} | {self.total:,.2f} COP")

    # Confirma solo si la transición es permitida y el servicio puede usarse.
    def confirmar(self, ocupada: bool) -> None:
        # La confirmación solo se admite desde el estado pendiente.
        if self.estado is not Estado.PENDIENTE:
            raise OperacionNoPermitida("Solo se puede confirmar una reserva pendiente")
        # La regla de ocupación es independiente de que el servicio esté activo.
        if ocupada or not self.servicio.disponible:
            raise ServicioNoDisponible("El servicio está ocupado o inactivo")
        # Aplica el cambio solo después de ambas comprobaciones.
        self.__estado = Estado.CONFIRMADA

    # Permite cancelar una solicitud pendiente o liberar una ya confirmada.
    def cancelar(self) -> None:
        # Rechaza reservas ya canceladas o procesadas.
        if self.estado not in (Estado.PENDIENTE, Estado.CONFIRMADA):
            raise OperacionNoPermitida("Solo se puede cancelar una reserva pendiente o confirmada")
        # Actualiza el estado para que la reserva deje de contar como confirmada.
        self.__estado = Estado.CANCELADA

    # Registra la ejecución de una reserva que ya fue confirmada.
    def procesar(self) -> None:
        # Rechaza procesar solicitudes que no estén confirmadas.
        if self.estado is not Estado.CONFIRMADA:
            raise OperacionNoPermitida("Solo se puede procesar una reserva confirmada")
        # Un servicio puede haber sido desactivado después de la confirmación.
        if not self.servicio.disponible:
            raise ServicioNoDisponible("El servicio no está activo para completar la reserva")
        # Cambia a procesada después de validar el estado y la disponibilidad.
        self.__estado = Estado.PROCESADA


class SistemaFJ:
    """Administra listas en memoria; una reserva confirmada ocupa el servicio."""

    # Prepara tres colecciones independientes que solo viven en memoria.
    def __init__(self) -> None:
        self.__clientes: list[Cliente] = []
        self.__servicios: list[Servicio] = []
        self.__reservas: list[Reserva] = []

    # La búsqueda sirve para listas de cualquier tipo de entidad del sistema.
    @staticmethod
    def _buscar(elementos: list[T], codigo: str) -> T:
        # Normaliza la clave con la misma regla del registro.
        clave = texto(codigo, "Código").upper()
        # Examina la colección hasta encontrar un código igual.
        for elemento in elementos:
            if elemento.codigo == clave:
                return elemento
        # Distingue una clave inexistente de una coincidencia válida.
        raise DatoInvalido("Código no encontrado")

    # Centraliza el alta y aplica el mismo control de duplicados a cada colección.
    @staticmethod
    def _agregar(elementos: list[T], nuevo: T) -> T:
        # Verifica la unicidad antes de modificar la lista.
        if any(elemento.codigo == nuevo.codigo for elemento in elementos):
            raise OperacionNoPermitida("Ya existe un elemento con ese código")
        # Incorpora el elemento validado y lo devuelve al solicitante.
        elementos.append(nuevo)
        return nuevo

    # Valida el cliente mediante su constructor antes de incorporarlo.
    def registrar_cliente(self, codigo: str, nombre: str, correo: str) -> Cliente:
        return self._agregar(self.__clientes, Cliente(codigo, nombre, correo))

    # Construye la especialización solicitada sin duplicar el flujo de alta.
    def crear_servicio(self, tipo: str, codigo: str, nombre: str, tarifa: object) -> Servicio:
        # Vincula los nombres aceptados en la entrada con sus clases concretas.
        clases = {"sala": Sala, "equipo": Equipo, "asesoria": Asesoria}
        try:
            # Normaliza el tipo antes de buscar la clase correspondiente.
            clase = clases[texto(tipo, "Tipo de servicio").lower()]
        # Conserva el KeyError para diagnóstico y presenta un error de negocio.
        except KeyError as causa:
            raise DatoInvalido("Tipo de servicio desconocido") from causa
        # Crea la instancia y registra su código en el catálogo.
        return self._agregar(self.__servicios, clase(codigo, nombre, tarifa))

    # Entrega un servicio por su código sin exponer toda la lista.
    def consultar_servicio(self, codigo: str) -> Servicio:
        return self._buscar(self.__servicios, codigo)

    # Comprueba si hay una reserva confirmada para esa misma instancia.
    def _ocupado(self, servicio: Servicio) -> bool:
        return any(r.servicio is servicio and r.estado is Estado.CONFIRMADA for r in self.__reservas)

    # Resuelve las referencias y solo guarda una reserva válida.
    def reservar(self, codigo: str, cod_cliente: str, cod_servicio: str,
                 duracion: object, **opciones: object) -> Reserva:
        # Verifica que el cliente exista en el registro.
        cliente = self._buscar(self.__clientes, cod_cliente)
        # Recupera el servicio que debe estar activo y desocupado.
        servicio = self._buscar(self.__servicios, cod_servicio)
        # Rechaza el servicio ocupado o inactivo antes de crear la reserva.
        if not servicio.disponible or self._ocupado(servicio):
            raise ServicioNoDisponible("El servicio está ocupado o inactivo")
        # Construye y valida la reserva antes de agregarla a la colección.
        return self._agregar(self.__reservas, Reserva(codigo, cliente, servicio, duracion, **opciones))

    # Busca la reserva y vuelve a comprobar la ocupación al confirmar.
    def confirmar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.confirmar(self._ocupado(reserva.servicio))
        return reserva

    # Busca la reserva y le delega el control de su transición a cancelada.
    def cancelar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.cancelar()
        return reserva

    # Busca la reserva y le delega el control del paso a procesada.
    def procesar(self, codigo: str) -> Reserva:
        reserva = self._buscar(self.__reservas, codigo)
        reserva.procesar()
        return reserva

    # Cambia el estado administrativo del servicio identificado y devuelve el resultado.
    def cambiar_disponibilidad(self, codigo: str, disponible: bool) -> Servicio:
        servicio = self._buscar(self.__servicios, codigo)
        servicio.cambiar_disponibilidad(disponible)
        return servicio


def configurar_log(ruta: str = "software_fj.log") -> logging.Logger:
    """Registra solo operaciones, estados y errores; no guarda datos de clientes."""
    # Reutiliza un registrador con nombre propio para el sistema.
    registro = logging.getLogger("software_fj")
    # Incluye información operativa además de los errores.
    registro.setLevel(logging.INFO)
    # Evita que los mensajes se repitan en el registrador general.
    registro.propagate = False
    # Cierra manejadores anteriores para no escribir entradas duplicadas.
    for anterior in tuple(registro.handlers):
        registro.removeHandler(anterior)
        anterior.close()
    # Abre la bitácora con codificación apta para los mensajes en español.
    salida = logging.FileHandler(ruta, encoding="utf-8")
    # Fija un formato uniforme con marca temporal, nivel y mensaje.
    salida.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    # Deja activa la salida al archivo solicitado.
    registro.addHandler(salida)
    return registro


def ejecutar(registro: logging.Logger, descripcion: str, accion: Callable[[], object]) -> object:
    """Aísla cada operación y registra el cierre, incluso después de un error."""
    # Registra el inicio antes de invocar la operación.
    registro.info("Inicio: %s", descripcion)
    try:
        # Ejecuta la función recibida sin acoplar el registro a una acción particular.
        resultado = accion()
    # Registra los errores conocidos del modelo sin reemplazar la excepción.
    except ErrorFJ as error:
        registro.error("%s: %s (%s)", descripcion, error, type(error).__name__)
        # Recorre la cadena de causas para identificar el origen técnico.
        causa = error.__cause__
        while causa is not None:
            # No se escribe el valor original ingresado en la bitácora.
            registro.info("Causa técnica: %s", type(causa).__name__)
            # Avanza a la siguiente causa del encadenamiento.
            causa = causa.__cause__
        # Propaga el error original para que el menú o la prueba pueda manejarlo.
        raise
    # Solo declara éxito si no se produjo una excepción.
    else:
        registro.info("Éxito: %s", descripcion)
        return resultado
    # Registra el cierre también cuando la operación falla.
    finally:
        registro.info("Cierre: %s", descripcion)
