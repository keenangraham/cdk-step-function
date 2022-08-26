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
from aws_cdk.aws_stepfunctions import Result

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

        succeed = Succeed(
            self,
            'Succeed',
        )

        get_stacks_to_delete_lambda = PythonFunction(
            self,
            'GetStacksToDeleteLambda',
            entry='cdk_step_function/runtime/cloudformation',
            runtime=Runtime.PYTHON_3_9,
            index='stacks.py',
            handler='get_stacks_to_delete',
            timeout=Duration.seconds(60),
        )

        get_stacks_to_delete_lambda.role.add_to_policy(
            PolicyStatement(
                actions=['cloudformation:DescribeStacks'],
                resources=['*'],
            )
        )

        loop_done = Pass(
            self,
            'LoopDone',
        )

        increment_counter_lambda = PythonFunction(
            self,
            'IncrementCounterLambda',
            entry='cdk_step_function/runtime/counter/',
            runtime=Runtime.PYTHON_3_9,
            index='increment.py',
            handler='increment_counter',
            timeout=Duration.seconds(60),
        )

        get_stacks_to_delete = LambdaInvoke(
            self,
            'GetStacksToDelete',
            lambda_function=get_stacks_to_delete_lambda,
            result_selector={
                'stacks_to_delete.$': '$.Payload'
            }
        )

        initialize_counter = Pass(
            self,
            'InitializeCounter',
            result=Result.from_object(
                {
                    'index': 0,
                    'step': 1,
                    'count': 3,
                }
            ),
            result_path='$.iterator',
        )

        increment_counter = LambdaInvoke(
            self,
            'IncrementCounter',
            lambda_function=increment_counter_lambda,
            result_selector={
                'index.$': '$.Payload.index',
                'step.$': '$.Payload.step',
                'count.$': '$.Payload.count',
                'continue.$': '$.Payload.continue',
            },
            result_path='$.iterator',
        )

        wait_ten_seconds = Wait(
            self,
            'WaitTenSeconds',
            time=WaitTime.duration(
                Duration.seconds(10)
            )
        )

        should_continue_loop = Choice(
            self,
            'ShouldContinueLoop'
        ).when(
            Condition.boolean_equals(
                '$.iterator.continue',
                True
            ),
            increment_counter
        ).otherwise(
            loop_done
        )

        stack_does_not_exist = Pass(
            self,
            'StackDoesNotExist',
        )

        describe_stack = CallAwsService(
            self,
            'DescribeStacks',
            service='cloudformation',
            action='describeStacks',
            iam_resources=['*'],
            parameters={
                'StackName.$': '$.stack_to_delete'
            }
        )

        describe_stack.add_catch(
            stack_does_not_exist,
            errors=[
                'CloudFormation.CloudFormationException'
            ]
        )

        delete_stack = CallAwsService(
            self,
            'DeleteStack',
            service='cloudformation',
            action='deleteStack',
            iam_resources=['*'],
            parameters={
                'StackName.$': '$.stack_to_delete'
            },
            result_path=JsonPath.DISCARD,
        )

        clean_up_routine = increment_counter.next(
            wait_ten_seconds
        ).next(
            should_continue_loop
        )

        map_stacks = Map(
            self,
            'MapStacks',
            items_path='$.stacks_to_delete',
            max_concurrency=5,
            parameters={
                'stack_to_delete.$': '$$.Map.Item.Value',
                'iterator.$': '$.iterator'
            }
        )

        map_stacks.iterator(clean_up_routine)

        definition = get_stacks_to_delete.next(
            initialize_counter
        ).next(
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
