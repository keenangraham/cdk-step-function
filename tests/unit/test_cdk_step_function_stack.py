import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_step_function.cdk_step_function_stack import CdkStepFunctionStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_step_function/cdk_step_function_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkStepFunctionStack(app, "cdk-step-function")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
