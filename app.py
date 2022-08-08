from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.aws_sns import Topic

from aws_cdk.aws_chatbot import SlackChannelConfiguration

from aws_cdk.aws_events import Rule
from aws_cdk.aws_events import EventPattern

from aws_cdk.aws_events_targets import SnsTopic
from aws_cdk.aws_events_targets import LambdaFunction

from aws_cdk.aws_lambda_python_alpha import PythonFunction

from aws_cdk.aws_lambda import Runtime

from aws_cdk.aws_ssm import StringParameter


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


app = App()

StepFunction(
    app,
    'StepFunction',
    env=US_WEST_2,
)

app.synth()
