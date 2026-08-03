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

            print(
                "Connecting to gateway..."
            )


            ws = websocket.create_connection(
                SERVER
            )


            print(
                "Connected to gateway"
            )



            while True:


                message = ws.recv()


                if not message:
                    break



                data = json.loads(
                    message
                )



                # =================================
                # SAVE IMAGE
                # =================================

                if data.get("type") == "save_image":


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


                    with open(
                        filepath,
                        "wb"
                    ) as f:

                        f.write(
                            image_data
                        )


                    print(
                        "Image saved:",
                        filepath
                    )



                    ws.send(
                        json.dumps({

                            "type":"saved",

                            "filename":filename

                        })
                    )




                # =================================
                # SEND IMAGE
                # =================================

                elif data.get("type") == "get_image":


                    filename = os.path.basename(
                        data["filename"]
                    )


                    filepath = os.path.join(
                        SAVE_PATH,
                        filename
                    )


                    print(
                        "Image requested:",
                        filepath
                    )



                    if os.path.exists(filepath):


                        with open(
                            filepath,
                            "rb"
                        ) as f:

                            image_data = f.read()



                        ws.send(
                            json.dumps({

                                "type":
                                    "image_response",

                                "filename":
                                    filename,

                                "image":
                                    base64.b64encode(
                                        image_data
                                    ).decode()

                            })
                        )


                        print(
                            "Image sent:",
                            filename
                        )



                    else:


                        ws.send(
                            json.dumps({

                                "type":
                                    "image_response",

                                "filename":
                                    filename,

                                "image":
                                    None

                            })
                        )


                        print(
                            "Image missing:",
                            filename
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