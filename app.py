from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration
from aws_cdk import Tags

from aws_cdk.aws_stepfunctions import Pass
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import StateMachine
from aws_cdk.aws_stepfunctions import LogOptions
from aws_cdk.aws_stepfunctions import LogLevel
from aws_cdk.aws_stepfunctions import Map
from aws_cdk.aws_stepfunctions import Choice
from aws_cdk.aws_stepfunctions import JsonPath
from aws_cdk.aws_stepfunctions import Condition

from aws_cdk.aws_iam import PolicyStatement

from aws_cdk.aws_stepfunctions_tasks import CallAwsService
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke

from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_lambda import Runtime

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.aws_logs import LogGroup
from aws_cdk import RemovalPolicy



class StackToDelete(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


class StepFunction(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        log_group = LogGroup(
            self,
            'LogGroup',
            removal_policy=RemovalPolicy.DESTROY,
        )

        get_stacks_to_delete = PythonFunction(
            self,
            'GetStacksToDelete',
            entry='cdk_step_function/runtime/cloudformation',
            runtime=Runtime.PYTHON_3_9,
            index='stacks.py',
            handler='get_stacks_to_delete',
            timeout=Duration.seconds(60),
        )

        get_stacks_to_delete.role.add_to_policy(
            PolicyStatement(
                actions=['cloudformation:DescribeStacks'],
                resources=['*'],
            )
        )

        no_op = Pass(
            self,
            'NoOp',
        )

        increment_counter = PythonFunction(
            self,
            'IncrementCounter',
            entry='cdk_step_function/runtime/counter/',
            runtime=Runtime.PYTHON_3_9,
            index='increment.py',
            handler='increment_counter',
            timeout=Duration.seconds(60),
        )

        call_get_stacks_to_delete = LambdaInvoke(
            self,
            'CallGetStacksToDelete',
            lambda_function=get_stacks_to_delete,
        )

        wait_five_seconds = Wait(
            self,
            'WaitFiveSeconds',
            time=WaitTime.duration(
                Duration.seconds(5)
            )
        )

        describe_stacks = CallAwsService(
            self,
            'DescribeStacks',
            service='cloudformation',
            action='describeStacks',
            iam_resources=['*'],
        )

        map_stacks = Map(
            self,
            'MapStacks',
            items_path='$.Payload',
            max_concurrency=5,
        )

        succeed = Succeed(
            self,
            'Succeed',
        )

        map_stacks.iterator(no_op)

        definition = call_get_stacks_to_delete.next(
            map_stacks
        ).next(
            succeed
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition,
            logs=LogOptions(
                destination=log_group,
                level=LogLevel.ALL,
                include_execution_data=True,
            )
        )


app = App()

step = StepFunction(
    app,
    'StepFunction',
    env=US_WEST_2,
)

delme = StackToDelete(
    app,
    'StackToDelete',
    env=US_WEST_2,
)


Tags.of(delme).add(
    'time-to-live-hours', '-1'
)


app.synth()
