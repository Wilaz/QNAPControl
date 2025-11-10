from typing import Callable
from enum import Enum
from serial import Serial
from threading import Thread

PREAMBLES = [0x53, 0x83]


class Response(Enum):
    ID = 0x01
    BUTTON = 0x05
    PROTOCOL = 0x08
    ACK = 0xFA
    NACK = 0xFB
    RACK = 0xAA


class Key(Enum):
    UP = bytes([0x00, 0x01])
    DOWN = bytes([0x00, 0x02])
    BOTH = bytes([0x00, 0x03])


class Commands(Enum):
    BASE = 0x4D
    ID = 0x00
    BUTTONS = 0x06
    PROTOCOL = 0x07
    DISPLAY_CHAR = 0x0C
    CLS = 0x0D
    BACKLIGHT = 0x5E
    RESET = 0xFF


class QnapLCD:
    def __init__(
        self,
        handler: Callable[[Response, int | Key | bytes | None], None] | None,
        port: str = "/dev/ttyS1",
        speed: int = 1200,
        rows: int = 2,
        columns: int = 16,
    ):
        self.serial: Serial = Serial(port, speed)
        self.columns: int = columns
        self.rows: int = rows

        if handler:
            self.handler: Callable[[Response, int | Key | bytes | None], None] = handler
            self.reader: Thread = Thread(target=self._handle_response)
            self.reader.start()

    def _handle_response(self):
        while True:
            if self.serial.read()[0] in PREAMBLES:
                match self.serial.read():
                    case Response.ID.value:
                        self.handler(Response.ID, int.from_bytes(self.serial.read(2)))

                    case Response.BUTTON.value:
                        self.handler(Response.BUTTON, Key(self.serial.read(2)))

                    case Response.PROTOCOL.value:
                        self.handler(
                            Response.PROTOCOL, int.from_bytes(self.serial.read(2))
                        )

                    case Response.RACK.value:
                        self.handler(Response.RACK, None)

                    case Response.ACK.value:
                        self.handler(Response.ACK, None)

                    case Response.NACK.value:
                        result = self.serial.read()
                        self.handler(Response.NACK, result)

                    case _:
                        raise Exception

    def clear(self):
        _ = self.serial.write(bytes([Commands.BASE.value, Commands.CLS.value]))

    def reset(self):
        _ = self.serial.write(bytes([Commands.BASE.value, Commands.RESET.value]))

    def get_id(self):
        _ = self.serial.write(bytes([Commands.BASE.value, Commands.ID.value]))

    def get_protocol(self):
        _ = self.serial.write(bytes([Commands.BASE.value, Commands.PROTOCOL.value]))

    def get_buttons(self):
        _ = self.serial.write(bytes([Commands.BASE.value, Commands.BUTTONS.value]))

    def backlight(self, on: bool = True):
        _ = self.serial.write(
            bytes([Commands.BASE.value, Commands.BACKLIGHT.value, 0x01 if on else 0x00])
        )

    def write(self, msg: str, row: int = 1):
        msg = msg[: self.columns]
        _ = self.serial.write(
            bytes(
                [
                    Commands.BASE.value,
                    Commands.DISPLAY_CHAR.value,
                    (row - 1) % self.rows,
                    len(msg),
                ]
            )
        )
        _ = self.serial.write(msg.encode("utf-8"))
