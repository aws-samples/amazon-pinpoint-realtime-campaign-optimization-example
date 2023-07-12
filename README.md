## Real-time Campaign Optimization with Pinpoint

The artifacts in this repository support the published blog: "Real-time Campaign Optimization with Pinpoint". Refer to the blog for detailed instructions on setup and configuration.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.


## Environment Setup

CDK Boostrap account
```
cdk bootstrap aws://<ACCOUNT-ID>/<REGION-NAME>
```

Setup environment and install requirements
```
python3 -m venv .env
source .env/bin/activate
pip3 install -r requirements.txt
``` 

Synthesize and Deploy the CDK Stack
``` 
cdk synth
cdk deploy "*" --require-approval never
``` 

Upgrade CDK (if necessary)
```
npm i -g aws-cdk --force
```