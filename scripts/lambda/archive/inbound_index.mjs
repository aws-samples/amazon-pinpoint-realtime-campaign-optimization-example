/*
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

import { PinpointClient, UpdateEndpointCommand } from "@aws-sdk/client-pinpoint";

const pinpoint = new PinpointClient({ region: process.env.region });
const projectId = process.env.projectId;

export const handler = async (event) => {
    for (const record of event.Records) {
        // Kinesis data is base64 encoded so decode here
        const payload = Buffer.from(record.kinesis.data, 'base64').toString('ascii');
        const payload_json = JSON.parse(payload);

        if (payload_json.data && payload_json.metadata && (payload_json.metadata.operation == 'insert' || payload_json.metadata.operation == 'update')) {
            var params = {
                ApplicationId: projectId,
                EndpointId: payload_json.data.email,
                EndpointRequest: {
                    ChannelType: 'CUSTOM',
                    Address: payload_json.data.email,
                    OptOut: 'NONE',
                    User: {
                        UserAttributes: {
                            Language: [
                                payload_json.data.language
                            ],
                            Favourites: [
                                payload_json.data.favourites
                            ]
                        },
                        UserId: payload_json.data.userid.toString()
                    }

                }
            }

            const command = new UpdateEndpointCommand(params);
            const response = await pinpoint.send(command);
        }
    }
    return `Successfully processed ${event.Records.length} records.`;
};
