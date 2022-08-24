from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration

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

from aws_cdk.aws_stepfunctions_tasks import CallAwsService

from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_lambda import Runtime

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2

from aws_cdk.aws_logs import LogGroup
from aws_cdk import RemovalPolicy

okay_statuses = [
    "CREATE_FAILED",
    "CREATE_COMPLETE",
    "ROLLBACK_FAILED",
    "ROLLBACK_COMPLETE",
    "DELETE_FAILED",
    "DELETE_COMPLETE",
    "UPDATE_COMPLETE",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_COMPLETE",
    "IMPORT_ROLLBACK_FAILED",
    "IMPORT_ROLLBACK_COMPLETE"
  ]


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

        increment_counter = PythonFunction(
            self,
            'IncrementCounter',
            entry='cdk_step_function/runtime/counter/',
            runtime=Runtime.PYTHON_3_9,
            index='increment.py',
            handler='increment_counter',
            timeout=Duration.seconds(60),
        )

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

        yes = Pass(
            self,
            'Yes',
        )

        no = Pass(
            self,
            'No',
        )

        succeed = Succeed(
            self,
            'Succeed',
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
            max_concurrency=5,
            items_path=JsonPath.string_at(
                '$.Stacks'
            )
        )

        status_conditions = Condition.or_(
            *[
                Condition.string_equals(
                    '$.StackStatus',
                    status
                )
                for status in okay_statuses
            ]
        )

        status_okay = Choice(
            self,
            'StatusOkay',
        ).when(
            status_conditions,
            yes
        ).otherwise(
            no
        )

        map_stacks.iterator(status_okay)

        definition = describe_stacks.next(
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


app.synth()
