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

import * as https from 'https';

const endpointURL = process.env.endpointURL;
const doPostRequest = (endpointURL, dataObj) => {

    const urlPath = '/' + endpointURL.split('/')[3];

    return new Promise((resolve, reject) => {
        const options = {
            host: 'webhook.site',
            path: urlPath,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        };

        //create the request object with the callback with the result
        const req = https.request(options, (res) => {
            resolve(JSON.stringify(res.statusCode));
        });

        // handle the possible errors
        req.on('error', (e) => {
            reject(e.message);
        });

        //do the request
        req.write(JSON.stringify(dataObj));

        //finish the request
        req.end();
    });
};


export const handler = async (event) => {
    if (event.Message && event.Endpoints) {
        for (const [id, endpoint] of Object.entries(event.Endpoints)) {
            const activationObj = { channel: 'SFMC', email: endpoint.Address };
            await doPostRequest(endpointURL, activationObj)
                .then(result => console.log(`Status code: ${result}`))
                .catch(err => console.error(`Error doing the request for the event: ${JSON.stringify(event)} => ${err}`));
        }
    }
};
