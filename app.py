from aws_cdk import App
from aws_cdk import Stack

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.aws_sns import Topic

from aws_cdk.aws_chatbot import SlackChannelConfiguration

from aws_cdk.aws_events import Rule
from aws_cdk.aws_events import EventPattern

from aws_cdk.aws_events_targets import SnsTopic


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
                SnsTopic(
                    event_notification_topic
                )
            ]
        )


app = App()

StepFunction(
    app,
    'StepFunction',
    env=US_WEST_2,
)

app.synth()
