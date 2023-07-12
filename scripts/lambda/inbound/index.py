import json
import boto3
import os
import base64

client = boto3.client('pinpoint')
projectId = os.environ.get("pinpointId")

def handler(event, context):
    print(event)
    records = event['Records']

    for payload_json in records:
        try:
            if "data" in payload_json['kinesis']:
                payload_json = base64.b64decode(payload_json["kinesis"]["data"]).decode("utf-8")
                payload_json = json.loads(payload_json)

                if ("metadata" in payload_json) and (payload_json["metadata"]["operation"] == 'insert' or payload_json["metadata"]["operation"] == 'update'):
                    params = {
                        "ApplicationId": projectId,
                        "EndpointId": payload_json["data"]["email"],
                        "EndpointRequest": {
                            "ChannelType": 'CUSTOM',
                            "Address": payload_json["data"]["email"],
                            "OptOut": 'NONE',
                            "User": {
                                "UserAttributes": {
                                    "Language": [
                                        payload_json["data"]["language"]
                                    ],
                                    "Favourites": []
                                },
                                "UserId":  str(payload_json["data"]["userid"])
                            }

                        }
                    }

                    if ("favourites" in payload_json["data"]):
                        params["EndpointRequest"]["User"]["UserAttributes"]["Favourites"].append(payload_json["data"]["favourites"])

                    print("##########################################")
                    print("Kinesis Event::")
                    print(payload_json)
                    print("Pinpoint Event::")
                    print(params)
                    print("##########################################")

                    response = client.update_endpoint(ApplicationId=params["ApplicationId"],EndpointId=params["EndpointId"],EndpointRequest=params["EndpointRequest"])
                    print(response)
                    print("Pinpoint Message Sent Successfully!!!")
                else:
                    raise Exception("No Key ([metadata]) found in event")
            else:
                raise Exception("No Key ([kinesis][data]) found in event")

        except Exception as e:
            print('Error: {}'.format(e))
            print('Current data: {}'.format(payload_json))

    no_of_records = len(records)
    return f"Successfully processed {no_of_records} records.";
