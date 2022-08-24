from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration

from aws_cdk.aws_stepfunctions import Pass
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import StateMachine

from aws_cdk.aws_stepfunctions_tasks import CallAwsService

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2


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

        list_stacks = CallAwsService(
            self,
            'ListStacks',
            service='cloudformation',
            action='listStacks',
        )

        definition = list_stacks.next(
            succeed
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition
        )


app = App()

step = StepFunction(
    app,
    'StepFunction',
    env=US_WEST_2,
)


app.synth()
