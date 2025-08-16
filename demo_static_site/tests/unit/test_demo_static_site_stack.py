import aws_cdk as core
import aws_cdk.assertions as assertions

from demo_static_site.demo_static_site_stack import DemoStaticSiteStack

# example tests. To run these tests, uncomment this file along with the example
# resource in demo_static_site/demo_static_site_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = DemoStaticSiteStack(app, "demo-static-site")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
