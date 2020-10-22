import boto3
import json

# Entrypoint from the jenkins script, everything inside __name__ == '__main__' will be executed
if __name__ == '__main__':

    """
    Create a cloudwatch dashboard with basic and custom widgets for
    monitoring performance of aqts-capture etl assets
    """

    region = 'us-west-2'

    cloudwatch_client  = boto3.client("cloudwatch", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)

    # set starting and default values for widget positioning and dimensions
    x, y = [0, 0]
    width, height = [3, 3]
    max_width = 12

    # initialize the array of widgets
    widgets = []

    print('Use print statements for diagnostics')

    # create lambda widgets
    # get all the lambdas in the account
    all_lambdas_response = lambda_client.list_functions(MaxItems=1000)
    for single_lambda in all_lambdas_response:
        metadata = lambda_client.get_function(single_lambda)
        tags = metadata.get_tags
        print(tags)