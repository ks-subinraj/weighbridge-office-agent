import websocket
import json
import base64
import os
import time


SAVE_PATH = os.path.join(
    os.getcwd(),
    "WB_IMAGES"
)

SERVER = "wss://muscatrecycling.com/wb/ws/office"


os.makedirs(
    SAVE_PATH,
    exist_ok=True
)


def connect():

    while True:

        try:

            print("Connecting to gateway...")

            ws = websocket.create_connection(
                SERVER
            )

            print("Connected to gateway")


            while True:

                message = ws.recv()


                if not message:
                    break


                data = json.loads(
                    message
                )


                # ==============================
                # RECEIVE IMAGE FROM ODOO
                # ==============================

                if data.get("type") == "image":


                    filename = os.path.basename(
                        data["filename"]
                    )


                    image_data = base64.b64decode(
                        data["image"]
                    )


                    filepath = os.path.join(
                        SAVE_PATH,
                        filename
                    )


                    with open(filepath, "wb") as file:

                        file.write(
                            image_data
                        )


                    print(
                        "Image saved:",
                        filepath
                    )


                    ws.send(
                        json.dumps({
                            "status": "saved",
                            "filename": filename
                        })
                    )



                # ==============================
                # SEND IMAGE TO GATEWAY
                # ==============================

                elif data.get("type") == "get_image":


                    filename = os.path.basename(
                        data["filename"]
                    )


                    filepath = os.path.join(
                        SAVE_PATH,
                        filename
                    )


                    if os.path.exists(filepath):


                        print(
                            "Sending image:",
                            filepath
                        )


                        with open(filepath, "rb") as file:

                            image_data = file.read()


                        ws.send_bytes(
                            image_data
                        )


                    else:

                        print(
                            "Image not found:",
                            filepath
                        )


        except Exception as e:

            print(
                "Connection error:",
                e
            )


        print(
            "Retrying in 5 seconds..."
        )


        time.sleep(5)



if __name__ == "__main__":

    connect()