

def handler(event, context):
    print(event)
    if ("Message" in event) and ("Endpoints" in event):
        for endpoint in event["Endpoints"]:
            activation_obj = { "channel": "SFMC", "email": endpoint }
            print(f"Campaign message sent for {activation_obj}")

    return {"statusCode": 200,"body": "Campaign Invoked Successfully"}
