from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration

from aws_cdk.aws_stepfunctions import Pass
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import StateMachine

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import ShellStep
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk import Tags

from aws_cdk.aws_chatbot import SlackChannelConfiguration


class StepFunction(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        wait_five_seconds = Wait(
            self,
            'WaitFiveSeconds',
            time=WaitTime.duration(
                Duration.seconds(5)
            )
        )

        no_op = Pass(
            self,
            'NoOp',
        )

        succeed = Succeed(
            self,
            'Succeed',
        )

        definition = wait_five_seconds.next(
            no_op
        ).next(
            succeed
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition
        )

        pipeline = CodePipeline(
            self,
            'Pipeline',
            self_mutation=True,
            synth=ShellStep(
                'Synth',
                input=CodePipelineSource.connection(
                    'keenangraham/cdk-step-function',
                    'main',
                    connection_arn='arn:aws:codestar-connections:us-west-2:618537831167:connection/077647ff-f9ef-406e-8392-e092848590f8'
                ),
                commands=[
                    'npm install -g aws-cdk@2.38.1',
                    'pip install -r requirements.txt -r requirements-dev.txt',
                    'cdk synth',
                ]
            )
        )

        pipeline.build_pipeline()

        chatbot = SlackChannelConfiguration(
            self,
            'encode-dcc-aws-chatbot',
            slack_channel_configuration_name='aws-chatbot',
            slack_workspace_id='T1KMV4JJZ',
            slack_channel_id='C034GTRCCLU',
        )
        pipeline.pipeline.notify_on_execution_state_change(
            'NotifyTest',
            chatbot
        )


app = App()

step = StepFunction(
    app,
    'StepFunction',
    env=US_WEST_2,
)

Tags.of(step).add(
    'test',
    'tag6',
#    include_resource_types=['AWS::CloudFormation::Stack'],
    exclude_resource_types=['AWS::CodeStarNotifications::NotificationRule']
)

app.synth()
