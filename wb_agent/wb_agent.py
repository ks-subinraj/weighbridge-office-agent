import asyncio
import json
import socket

import serial
import serial.tools.list_ports
import websockets

from fastapi import FastAPI
from contextlib import asynccontextmanager



# ==============================
# CONFIG
# ==============================

GATEWAY_URL = "wss://muscatrecycling.com/wb/ws/weighbridge"


BAUDRATE = 9600



# ==============================
# DEVICE ID
# ==============================

def get_device_id():

    return socket.gethostname().upper()



DEVICE_ID = get_device_id()



print(
    "Device ID:",
    DEVICE_ID
)



# ==============================
# GLOBALS
# ==============================

ser = None


latest_weight = {

    "device_id": DEVICE_ID,

    "weight": 0,

    "unit": "kg",

    "stable": False

}



# ==============================
# FIND WEIGHBRIDGE
# ==============================

def find_serial():


    print("Searching serial ports...")


    for port in serial.tools.list_ports.comports():

        try:

            print(
                "Testing:",
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


                print(
                    "Weighbridge found:",
                    port.device
                )


                return test



            test.close()



        except Exception:

            pass



    return None





# ==============================
# READ WEIGHT
# ==============================

async def serial_reader():

    global latest_weight


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


                    print(
                        "RAW:",
                        data
                    )


                    parts = data.split(",")



                    #
                    # Example:
                    # ST,GS,12540,kg
                    #


                    if len(parts) >= 4:


                        try:


                            latest_weight = {


                                "device_id":
                                DEVICE_ID,


                                "weight":
                                float(
                                    parts[2]
                                    .strip()
                                ),


                                "unit":
                                parts[3]
                                .strip(),


                                "stable":
                                True

                            }



                        except Exception:

                            pass




        except Exception as e:


            print(
                "Serial error:",
                e
            )



        await asyncio.sleep(
            0.05
        )







# ==============================
# CONNECT TO GATEWAY
# ==============================

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


            print(
                "Connecting:",
                url
            )


            async with websockets.connect(

                url,

                ping_interval=20,

                ping_timeout=20

            ) as websocket:



                print(
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


            print(
                "Gateway error:",
                e
            )


            print(
                "Retrying in 5 seconds..."
            )


            await asyncio.sleep(
                5
            )







# ==============================
# FASTAPI STATUS
# ==============================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global ser



    print(
        "Starting Weighbridge Agent"
    )



    print(
        "Device:",
        DEVICE_ID
    )



    ser = find_serial()



    if ser:


        print(
            "Serial connected"
        )


        asyncio.create_task(
            serial_reader()
        )


    else:


        print(
            "No weighbridge found"
        )



    asyncio.create_task(
        gateway_client()
    )



    yield



    if ser:

        ser.close()






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


        "weight":
        latest_weight

    }






# ==============================
# START
# ==============================

if __name__ == "__main__":


    import uvicorn


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=9000

    )