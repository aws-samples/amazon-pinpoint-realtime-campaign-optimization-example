from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    aws_kinesis as kinesis,
    aws_lambda_nodejs as lambda_,
    aws_lambda,
    aws_pinpoint as pinpoint,
    aws_secretsmanager as secretsmanager,
    aws_dms as dms,
    Aspects,Stack,Aws,CfnOutput,
    aws_lambda_event_sources,
    Duration,
)
from constructs import Construct, DependencyGroup

import config as cf

import json
import os

from cdk_nag import ( AwsSolutionsChecks, NagSuppressions )

class ApplicationStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,**kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)


    Aspects.of(self).add(AwsSolutionsChecks())
    ##
    ## Supressed Checks
    ##
    NagSuppressions.add_stack_suppressions(self, [{"id":"AwsSolutions-IAM4", "reason":"TODO: Stop using AWS managed policies."}])
    NagSuppressions.add_stack_suppressions(self, [{"id":"AwsSolutions-IAM5", "reason":"TODO: Remove Wildcards in IAM roles."}])
    NagSuppressions.add_stack_suppressions(self, [{"id":"AwsSolutions-RDS10", "reason":"TODO: Enable Deletion Protection."}])
    NagSuppressions.add_stack_suppressions(self, [{"id":"AwsSolutions-RDS15", "reason":"TODO: Enable Deletion Protection."}])

    ## Variable Initialization
    cdk_account_id:str = os.environ["CDK_DEFAULT_ACCOUNT"] 

    ########################################
    ##
    ## VPC Resources
    ##
    #########################################
    
    vpc = ec2.Vpc.from_lookup(
      self,
      "vpc",
      vpc_id=cf.vpc_id)
        
    subnets = []  
    for s in cf.subnet_ids:
      subnets.append(ec2.Subnet.from_subnet_id(self, s, s))

    vpc.add_interface_endpoint("KinesisEndPoint",
                                    service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{Aws.REGION}.kinesis-streams'),
                                    subnets=ec2.SubnetSelection(
                                      subnets=subnets)
                                    )

    # vpc.add_interface_endpoint("SecretsManagerEndPoint",
    #                            service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{Aws.REGION}.secretsmanager'),
    #                            subnets=ec2.SubnetSelection(
    #                                subnets=subnets)
    #                            )
    #
    # vpc.add_interface_endpoint("KmsEndPoint",
    #                            service=ec2.InterfaceVpcEndpointService(f'com.amazonaws.{Aws.REGION}.kms'),
    #                            subnets=ec2.SubnetSelection(
    #                                subnets=subnets)
    #                            )

    ####################################
    ##
    ## IAM Resources
    ##
    ####################################

    pinpoint_iam_policy = iam.ManagedPolicy(self, 
                        f"{cf.namespace}_pinpoint_iam_policy",
                        description         = "Pinpoint IAM Policy")

    pinpoint_iam_policy.add_statements(iam.PolicyStatement(effect   =iam.Effect.ALLOW,
                                                                     actions  =["mobiletargeting:UpdateEndpoint"],
                                                                     resources=[
                                                                       f'arn:aws:mobiletargeting:{Aws.REGION}:{Aws.ACCOUNT_ID}:apps/*/endpoints/*',
                                                                       ]))

    lambda_execution_role = iam.Role(self,
                             id=f"{cf.namespace}_lambda_execution_role",
                             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
                             )
    lambda_execution_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaKinesisExecutionRole"))
    lambda_execution_role.add_managed_policy(pinpoint_iam_policy)

    self.dms_role = iam.Role(self,
                             id=f"{cf.namespace}_dms_role",
                             assumed_by=iam.ServicePrincipal(f"dms.{Aws.REGION}.amazonaws.com"),
                             inline_policies={
                                                "Policy_KMS": iam.PolicyDocument(statements=[
                                                              iam.PolicyStatement(effect=iam.Effect.ALLOW,
                                                              principals=[f"dms.{Aws.REGION}.amazonaws.com"],
                                                              resources=[f"arn:aws:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:*"],
                                                              actions=["kms:Encrypt",
                                                                       "kms:Decrypt",
                                                                       "kms:ReEncrypt",
                                                                       "kms:GenerateDataKey",
                                                                       "kms:DescribeKey"])]),
                                                "Policy_KINESIS": iam.PolicyDocument(statements=[
                                                                  iam.PolicyStatement(effect=iam.Effect.ALLOW,
                                                                     principals=[f"com.amazonaws.{Aws.REGION}.kinesis-streams"],
                                                                     resources=[f"arn:aws:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:*"],
                                                                     actions=["kinesis:PutRecords",
                                                                              "kinesis:DescribeStream"])]),
                                            })

    # self.dms_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonKinesisFullAccess"))
    # self.dms_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"))
    
    if cf.create_dms_service_role:
      dms_vpc_role = iam.Role(self,
                               id="dms-vpc-role",
                               role_name="dms-vpc-role",
                               assumed_by=iam.ServicePrincipal(f"dms.amazonaws.com")
                               )
      dms_vpc_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonDMSVPCManagementRole"))
    else:
      dms_service_role_arn = cf.dms_service_role_arn
  

    ####################################
    ##
    ## RDS Resources
    ##
    ####################################  
    self.sg_rds = ec2.SecurityGroup(self, 
                                          id='sg_rds',
                                          vpc=vpc,
                                          allow_all_outbound=True,
                                          description='Security Group for RDS MySQL')
    self.sg_rds.add_ingress_rule(peer=self.sg_rds,
                                      connection=ec2.Port.all_traffic())
                                      
    self.sg_rds.add_ingress_rule(peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
                                      connection=ec2.Port.all_traffic())                                      

    templated_rds_secret = secretsmanager.Secret(self, "TemplatedRdsSecret",
          generate_secret_string=secretsmanager.SecretStringGenerator(
            secret_string_template=json.dumps({"username": "admin"}),
            generate_string_key="password",
            exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"
        )
    )
    
    self.rds_mysql_instance = rds.DatabaseInstance(self,
                                                  "rds_mysql_instance",
                                                  engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0_32),
                                                  vpc_subnets=ec2.SubnetSelection(subnets=subnets),
                                                  vpc=vpc,
                                                  instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
                                                  allocated_storage=20,
                                                  credentials=rds.Credentials.from_secret(templated_rds_secret),
                                                  publicly_accessible=False,
                                                  deletion_protection=False,
                                                  parameters = {
                                                    'binlog_format': 'ROW'
                                                  },
                                                  port=cf.port,
                                                  security_groups = [self.sg_rds],
                                                  storage_encrypted = True,
                                                  storage_type=rds.StorageType.GP2)

    secretsmanager.SecretRotation(self, "SecretRotation",
        application=secretsmanager.SecretRotationApplication.MYSQL_ROTATION_SINGLE_USER,
        secret=templated_rds_secret,
        target=self.rds_mysql_instance,  
        vpc=vpc,  
        exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"
    )

    ####################################
    ##
    ## Kinesis Resources
    ##
    ####################################
    kinesis_stream = kinesis.Stream(self,
                                        "kinesis_stream",
                                        shard_count=1)


    # ####################################
    # ##
    # ## DMS Resources
    # ##
    # ####################################
                                        
    dms_source_endpoint = dms.CfnEndpoint(self, 
      "RdsEndpoint",
      endpoint_type="source",
      engine_name="mysql",
      my_sql_settings=dms.CfnEndpoint.MySqlSettingsProperty(
          secrets_manager_access_role_arn=self.dms_role.role_arn,
          secrets_manager_secret_id=templated_rds_secret.secret_full_arn
      )
    )

    dms_target_endpoint = dms.CfnEndpoint(self, 
      "KinesisEndpoint",
      endpoint_type="target",
      engine_name="kinesis",
      kinesis_settings = dms.CfnEndpoint.KinesisSettingsProperty(
        message_format="JSON",
        service_access_role_arn=self.dms_role.role_arn,
        stream_arn= kinesis_stream.stream_arn
      )
    )
    
    dms_replication_subnet_group = dms.CfnReplicationSubnetGroup(self, "DmsReplicationSubnetGroup",
        replication_subnet_group_description = 'DMS Replication Subnet Group',
        subnet_ids=cf.subnet_ids
    )
    
    dms_replication_subnet_group.node.add_dependency(dms_vpc_role)

    dms_replication_instance = dms.CfnReplicationInstance(self, "DmsReplicationInstance",
        replication_instance_class="dms.t3.medium",
        replication_subnet_group_identifier = dms_replication_subnet_group.ref,#.replication_subnet_group_identifier,
        allocated_storage=50,
        engine_version="3.4.7",
        multi_az=False,
        publicly_accessible=True
    )
    
    dms_replication_instance.node.add_dependency(dms_vpc_role)

    dms_replication_task = dms.CfnReplicationTask(self, "DmsReplicationTask",
        migration_type="full-load-and-cdc",
        replication_instance_arn=dms_replication_instance.ref,
        source_endpoint_arn=dms_source_endpoint.ref,
        table_mappings='''{ \"rules\": [ { \"rule-type\": \"selection\", 
          \"rule-id\": \"1\", \"rule-name\": \"1\", \"object-locator\": 
            { \"schema-name\": \"sys\", \"table-name\": \"%\" }, \"rule-action\": \"exclude\" }, 
            { \"rule-type\": \"selection\", \"rule-id\": \"2\", 
            \"rule-name\": \"2\", \"object-locator\": { \"schema-name\": \"pinpoint-test-db\", 
            \"table-name\": \"customer_tb\" }, \"rule-action\": \"include\" } ] }''',
        target_endpoint_arn=dms_target_endpoint.ref
    )
    
    ####################################
    ##
    ## Pinpoint Project
    ##
    ####################################
    pinpoint_app = pinpoint.CfnApp(self,
                                        "pinpoint_project",
                                        name=f"{cf.namespace}-pinpoint-project")
                                        
    ####################################
    ##
    ## Lambda Functions
    ##
    ####################################

    lambda_inbound_function = aws_lambda.Function(self, "lambda_inbound_function",
        runtime=aws_lambda.Runtime.PYTHON_3_9,
        handler="index.handler",
        code=aws_lambda.Code.from_asset("./scripts/lambda/inbound"),
        role=lambda_execution_role,
        timeout=Duration.seconds(900),
        environment={
          "region": f"{Aws.REGION}",
          "pinpointId": pinpoint_app.ref
        }
    )

    lambda_inbound_function.add_event_source(aws_lambda_event_sources.KinesisEventSource(
        kinesis_stream,
        batch_size=1, 
        starting_position=aws_lambda.StartingPosition.LATEST
    ))

    lambda_outbound_function = aws_lambda.Function(self, "lambda_outbound_function",
        runtime=aws_lambda.Runtime.PYTHON_3_9,
        handler="index.handler",
        code=aws_lambda.Code.from_asset("./scripts/lambda/outbound"),
        role=lambda_execution_role,
        timeout=Duration.seconds(900)
    )

    lambda_outbound_function.add_permission("LambdaInvocation",
                                        principal=iam.ServicePrincipal(f'pinpoint.{Aws.REGION}.amazonaws.com'),
                                        action ="lambda:InvokeFunction",
                                        source_arn=f'arn:aws:mobiletargeting:{Aws.REGION}:{Aws.ACCOUNT_ID}:apps/*'
                                        )


    ####################################
    ##
    ## Cfn Output
    ##
    ####################################

    CfnOutput(self, "RDS_Secret_Name",
      value       = templated_rds_secret.secret_name,
      description = "Secret Name for RDS MySQL Instance"
    )
    CfnOutput(self, "Pinpoint_Project_Id",
      value       = pinpoint_app.ref,
      description = "Pinpoint Project Id"
    )

    CfnOutput(self, "Pinpoint_Project_Name",
      value       = pinpoint_app.name,
      description = "Pinpoint Project Name"
    )    
                                      
