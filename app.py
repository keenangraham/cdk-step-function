from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import Duration
from aws_cdk import Tags

from aws_cdk.aws_ssm import StringParameter

from aws_cdk.aws_stepfunctions import Pass
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import Fail
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



class ProducerToDelete(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.value = StringParameter(
            self,
            'ProducerValue',
            string_value='ProducerValue'
        )


class ConsumerToDelete(Stack):
    def __init__(self, scope: Construct, construct_id: str, producer: Stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.producer = producer
        StringParameter(
            self,
            'SomeReferenceValue',
            string_value=self.producer.value.parameter_arn
        )


class StepFunction(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        log_group = LogGroup(
            self,
            'LogGroup',
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.log_group = log_group

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

        delete_sucessful = Succeed(
            self,
            'DeleteSuccessful'
        )

        unable_to_delete = Pass(
            self,
            'UnableToDelete'
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
            payload_response_only=True,
            result_selector={
                'stacks_to_delete.$': '$'
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
            payload_response_only=True,
            result_path='$.iterator',
        )

        wait_ten_seconds = Wait(
            self,
            'WaitTenSeconds',
            time=WaitTime.duration(
                Duration.seconds(10)
            )
        )

        should_try_again = Choice(
            self,
            'ShouldTryAgain'
        ).when(
            Condition.boolean_equals(
                '$.iterator.continue',
                True
            ),
            increment_counter
        ).otherwise(
            unable_to_delete
        )

        does_stack_exist = CallAwsService(
            self,
            'DoesStackExist',
            service='cloudformation',
            action='describeStacks',
            iam_resources=['*'],
            parameters={
                'StackName.$': '$.stack_to_delete'
            },
            result_path=JsonPath.DISCARD,
        )

        does_stack_exist.add_catch(
            delete_sucessful,
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

        delete_stack.add_catch(
            unable_to_delete,
            errors=[
                'CloudFormation.CloudFormationException'
            ]
        )

        clean_up_routine = increment_counter.next(
            delete_stack
        ).next(
            wait_ten_seconds
        ).next(
            does_stack_exist
        ).next(
            should_try_again
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

producer = ProducerToDelete(
    app,
    'ProducerToDelete',
    env=US_WEST_2,
)

consumer = ConsumerToDelete(
    app,
    'ConsumerToDelete2',
    producer=producer,
    env=US_WEST_2,
)


Tags.of(producer).add(
    'time-to-live-hours', '-1'
)

Tags.of(consumer).add(
    'time-to-live-hours', '-1'
)


app.synth()
