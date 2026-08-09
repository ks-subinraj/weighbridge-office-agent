import asyncio
import json
import socket
import logging

import serial
import serial.tools.list_ports
import websockets

from fastapi import FastAPI
from contextlib import asynccontextmanager


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename="wb_agent.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("wb_agent")


# ============================================================
# CONFIG
# ============================================================

GATEWAY_URL = "wss://muscatrecycling.com/wb/ws/weighbridge"

# Dini Argeo TCP connection
SCALE_IP = "192.168.16.205"
SCALE_PORT = 23

# Serial fallback
BAUDRATE = 9600


# ============================================================
# DEVICE ID
# ============================================================

def get_device_id():

    return socket.gethostname().upper()


DEVICE_ID = get_device_id()


logger.info(
    "Device ID: %s",
    DEVICE_ID
)


# ============================================================
# GLOBALS
# ============================================================

ser = None

tcp_socket = None

connection_type = None


latest_weight = {

    "device_id": DEVICE_ID,

    "weight": 0,

    "unit": "kg",

    "stable": False
}


# ============================================================
# PARSE WEIGHT
# ============================================================

def parse_weight(data):

    try:

        data = data.strip()

        if not data:
            return None

        parts = [
            part.strip()
            for part in data.split(",")
        ]

        if len(parts) < 4:
            return None

        status = parts[0]
        mode = parts[1]
        weight = float(parts[2])
        unit = parts[3]

        return {
            "device_id": DEVICE_ID,
            "weight": weight,
            "unit": unit,
            "stable": status != "US",
            "status": status,
            "mode": mode,
        }

    except Exception as e:

        logger.error(
            "Weight parse error: %s | data=%r",
            e,
            data
        )

        return None


# ============================================================
# SERIAL
# ============================================================

def find_serial():

    logger.info(
        "Searching serial ports..."
    )


    for port in serial.tools.list_ports.comports():

        try:

            logger.info(
                "Testing serial port: %s",
                port.device
            )


            test = serial.Serial(

                port=port.device,

                baudrate=BAUDRATE,

                bytesize=serial.EIGHTBITS,

                parity=serial.PARITY_NONE,

                stopbits=serial.STOPBITS_ONE,

                timeout=1
            )


            data = (
                test.readline()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
                .strip()
            )


            if data:

                logger.info(
                    "Weighbridge found on serial: %s",
                    port.device
                )


                return test


            test.close()


        except Exception as e:

            logger.info(
                "Serial test failed %s: %s",
                port.device,
                e
            )


    return None


# ============================================================
# SERIAL READER
# ============================================================

async def serial_reader():

    global latest_weight


    logger.info(
        "Serial reader started"
    )


    while True:

        try:

            if ser:

                data = (
                    ser.readline()
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                    .strip()
                )


                if data:

                    logger.info(
                        "Serial RAW: %s",
                        repr(data)
                    )


                    parsed = parse_weight(
                        data
                    )


                    if parsed:

                        latest_weight = parsed


                        logger.info(
                            "SERIAL WEIGHT: %s %s",
                            parsed["weight"],
                            parsed["unit"]
                        )


        except Exception as e:

            logger.error(
                "Serial reader error: %s",
                e
            )


        await asyncio.sleep(
            0.05
        )


# ============================================================
# TCP SCALE CONNECTION
# ============================================================

def connect_tcp_scale():

    logger.info(
        "Connecting to Dini Argeo TCP scale: %s:%s",
        SCALE_IP,
        SCALE_PORT
    )


    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )


    sock.settimeout(5)


    sock.connect(
        (
            SCALE_IP,
            SCALE_PORT
        )
    )


    logger.info(
        "Dini Argeo TCP connected"
    )


    return sock


# ============================================================
# TCP SCALE READER
# ============================================================

async def tcp_scale_reader():

    global tcp_socket
    global latest_weight


    logger.info(
        "TCP scale reader started"
    )


    while True:

        try:

            tcp_socket = connect_tcp_scale()


            buffer = ""


            while True:

                data = await asyncio.to_thread(
                    tcp_socket.recv,
                    4096
                )


                if not data:

                    logger.warning(
                        "TCP scale connection closed"
                    )

                    break


                text = data.decode(
                    "ascii",
                    errors="ignore"
                )


                logger.info(
                    "TCP RAW CHUNK: %r",
                    text
                )


                buffer += text


                # TCP does NOT preserve message boundaries.
                #
                # Example:
                #
                # chunk 1:
                # ZR,GS,
                #
                # chunk 2:
                #       1250,kg\r\n
                #
                # So wait until \r\n exists.

                while "\r\n" in buffer:

                    line, buffer = buffer.split(
                        "\r\n",
                        1
                    )


                    line = line.strip()


                    if not line:

                        continue


                    logger.info(
                        "TCP SCALE LINE: %s",
                        repr(line)
                    )


                    parsed = parse_weight(
                        line
                    )


                    if parsed:

                        latest_weight = parsed


                        logger.info(
                            "TCP WEIGHT: %s %s",
                            parsed["weight"],
                            parsed["unit"]
                        )


        except Exception as e:

            logger.error(
                "TCP scale error: %s",
                e
            )


        finally:

            if tcp_socket:

                try:

                    tcp_socket.close()

                except Exception:

                    pass


                tcp_socket = None


        logger.info(
            "Retrying TCP scale in 5 seconds..."
        )


        await asyncio.sleep(
            5
        )


# ============================================================
# GATEWAY CLIENT
# ============================================================

async def gateway_client():

    url = (
        GATEWAY_URL
        +
        "/"
        +
        DEVICE_ID
    )


    while True:

        try:

            logger.info(
                "Connecting gateway: %s",
                url
            )


            async with websockets.connect(

                url,

                ping_interval=20,

                ping_timeout=20

            ) as websocket:


                logger.info(
                    "Gateway connected"
                )


                while True:

                    await websocket.send(
                        json.dumps(
                            latest_weight
                        )
                    )


                    await asyncio.sleep(
                        0.5
                    )


        except Exception as e:

            logger.error(
                "Gateway error: %s",
                e
            )


            logger.info(
                "Retrying gateway in 5 seconds..."
            )


            await asyncio.sleep(
                5
            )


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global ser
    global connection_type


    logger.info(
        "========================================"
    )

    logger.info(
        "Starting Weighbridge Agent"
    )

    logger.info(
        "Device: %s",
        DEVICE_ID
    )

    logger.info(
        "========================================"
    )


    # --------------------------------------------------------
    # FIRST: TRY TCP Dini Argeo
    # --------------------------------------------------------

    try:

        test_socket = connect_tcp_scale()


        test_socket.close()


        connection_type = "tcp"


        logger.info(
            "Dini Argeo detected through TCP"
        )


        asyncio.create_task(
            tcp_scale_reader()
        )


    except Exception as e:

        logger.warning(
            "TCP scale unavailable: %s",
            e
        )


        # ----------------------------------------------------
        # FALLBACK: SERIAL
        # ----------------------------------------------------

        ser = find_serial()


        if ser:

            connection_type = "serial"


            logger.info(
                "Using serial weighbridge"
            )


            asyncio.create_task(
                serial_reader()
            )


        else:

            connection_type = None


            logger.warning(
                "No weighbridge found"
            )


    # --------------------------------------------------------
    # GATEWAY
    # --------------------------------------------------------

    asyncio.create_task(
        gateway_client()
    )


    yield


    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    if ser:

        try:

            ser.close()

        except Exception:

            pass


    if tcp_socket:

        try:

            tcp_socket.close()

        except Exception:

            pass


    logger.info(
        "Weighbridge Agent stopped"
    )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    lifespan=lifespan
)


@app.get("/")
def home():

    return {

        "status":
            "running",

        "device_id":
            DEVICE_ID,

        "connection":
            connection_type,

        "scale_ip":
            SCALE_IP,

        "scale_port":
            SCALE_PORT,

        "weight":
            latest_weight

    }


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=9000,

        log_config=None,

        access_log=False
    )
