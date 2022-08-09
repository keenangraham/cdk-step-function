import json

from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.aws_sns import Topic

from aws_cdk.aws_chatbot import SlackChannelConfiguration

from aws_cdk.aws_events import EventBus
from aws_cdk.aws_events import Rule
from aws_cdk.aws_events import EventPattern

from aws_cdk.aws_events_targets import SnsTopic
from aws_cdk.aws_events_targets import LambdaFunction

from aws_cdk.aws_lambda_python_alpha import PythonFunction

from aws_cdk.aws_lambda import Runtime

from aws_cdk.aws_ssm import StringParameter

from aws_cdk.aws_s3_assets import Asset

from aws_cdk.custom_resources import AwsCustomResource
from aws_cdk.custom_resources import AwsCustomResourcePolicy
from aws_cdk.custom_resources import AwsSdkCall
from aws_cdk.custom_resources import PhysicalResourceId

from aws_cdk.aws_logs import RetentionDays


class StepFunction(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

        super().__init__(scope, construct_id, **kwargs)

        event_channel = SlackChannelConfiguration(
            self,
            'EventChannel',
            slack_channel_configuration_name='aws-events',
            slack_workspace_id='T1KMV4JJZ',
            slack_channel_id='C03QPGPLAMQ',
        )

        event_notification_topic = Topic(
            self,
            'EventNotificationTopic',
        )

        event_channel.add_notification_topic(
            event_notification_topic
        )

        slack_webhook_url = StringParameter.from_string_parameter_name(
            self,
            'SlackWebhookUrl',
            string_parameter_name='DEMO_EVENTS_SLACK_WEBHOOK_URL'
        )

        send_event_details_to_slack = PythonFunction(
            self,
            'SendEventDetailsToSlack',
            entry='runtime/lambda/',
            runtime=Runtime.PYTHON_3_9,
            index='slack.py',
            handler='handler',
            timeout=Duration.seconds(60),
            environment={
                'SLACK_WEBHOOK_URL': slack_webhook_url.string_value
            }
        )

        rule = Rule(
            self,
            'CustomEventNotificationRule',
            event_pattern=EventPattern(
                detail_type=[
                    'CustomEvent',
                ],
                source=[
                    'some.custom.event',
                ],
            ),
            targets=[
                LambdaFunction(
                    send_event_details_to_slack,
                ),
            ]
        )

        lambda_asset = Asset(
            self,
            'LambdaAsset',
            path='runtime/lambda/',
        )

        slack_text = json.dumps(
             {
                 'text': 'asset hash updated, custom event triggered, update message'
             }
        )

        event_bus = EventBus.from_event_bus_arn(
            self,
            'DefaultBust',
            'arn:aws:events:us-west-2:618537831167:event-bus/default',
        )

        put_custom_event = AwsCustomResource(
            self,
            'PutCustomEvent',
            on_update=AwsSdkCall(
                service='EventBridge',
                action='putEvents',
                parameters={
                    'Entries': [
                        {
                            'DetailType': 'CustomEvent',
                            'Source': 'some.custom.event',
                            'Detail': slack_text,
                        }
                    ]
                },
                physical_resource_id=PhysicalResourceId.of(
                    lambda_asset.asset_hash
                )
            ),
            log_retention=RetentionDays.ONE_DAY,
            policy=AwsCustomResourcePolicy.from_sdk_calls(
                resources=[
                    event_bus.event_bus_arn,
                ]
            )
        )

        event_bus.grant_put_events_to(put_custom_event)


app = App()

StepFunction(
    app,
    'StepFunction2',
    env=US_WEST_2,
)

app.synth()
