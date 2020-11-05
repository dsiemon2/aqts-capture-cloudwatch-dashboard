"""
module for creating sqs widgets

"""

import boto3
from .lookups import sqs_queues


def create_sqs_widgets(region, deploy_stage, positioning):
    """
    Creates the list of SQS widgets.

    :param region: Typically 'us-west-2'
    :param deploy_stage: The deploy tier, DEV, TEST, QA, PROD-EXTERNAL
    :param positioning: The x, y, height, width coordinates and dimensions on the dashboard
    :return: list of SQS widgets
    :rtype: list
    """
    sqs_widgets = []

    # grab all the sqs queue urls in the account/region
    all_sqs_queue_urls_response = get_all_sqs_queue_urls(region)

    # iterate over the list of queue urls and create widgets for the assets we care about based on filters
    for queue_url in all_sqs_queue_urls_response['QueueUrls']:
        if is_iow_queue_filter(queue_url, deploy_stage, region):

            # incoming queue url: https://us-west-2.queue.amazonaws.com/579777464052/aqts-capture-error-queue-TEST
            # we want the queue name after the last "/"
            url_parts = queue_url.split('/')
            queue_name = url_parts[-1]

            tier_agnostic_queue_name = queue_name.replace(f"-{deploy_stage}", '')
            queue_title = sqs_queues[tier_agnostic_queue_name]['title']

            # sqs queues take up half the 24 column grid
            positioning.width = 12

            queue_widget = {
                'type': 'metric',
                'x': positioning.x,
                'y': positioning.y,
                'height': positioning.height + 3,
                'width': positioning.width,
                'properties': {
                    "metrics": [
                        ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", queue_name],
                        [".", "ApproximateAgeOfOldestMessage", ".", ".", {"yAxis": "right"}],
                        [".", "NumberOfMessagesReceived", ".", ".", {"stat": "Sum"}],
                        [".", "NumberOfMessagesSent", ".", ".", {"stat": "Sum"}],
                        [".", "NumberOfMessagesDeleted", ".", "."],
                        [".", "ApproximateNumberOfMessagesDelayed", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "period": 60,
                    "title": queue_title,
                    "stat": "Average",

                }
            }

            sqs_widgets.append(queue_widget)
            positioning.iterate_positioning()

    return sqs_widgets


def get_all_sqs_queue_urls(region):
    """
    Using the AWS python sdk (boto3), grab all the sqs queue urls for the specified account for a given region.

    :param region: The region, for us that's usually us-west-2
    :return: response: a page of sqs urls in the account.
    :rtype: dict
    """
    sqs_client = boto3.client("sqs", region_name=region)

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.list_queues
    # TODO this pagination logic exists in the lambdas module as well, consider moving it into its own utility
    # TODO module or trying to get a proper boto3 paginator to work...
    response = {}
    next_token = None
    while True:
        if next_token:
            response_iterator = sqs_client.list_queues(
                    # MaxResults has to be set in order to receive a pagination token in the response
                    MaxResults=10,
                    NextToken=next_token)
            response['QueueUrls'].extend(response_iterator['QueueUrls'])
        else:
            response_iterator = sqs_client.list_queues(
                    MaxResults=10
            )
            response.update(response_iterator)
        try:
            next_token = response_iterator['NextToken']
        except KeyError:
            # no more pages, move on
            break

    return response


def is_iow_queue_filter(queue_url, deploy_stage, region):
    """
    Apply filters to determine if the queue is a tagged IOW asset in the correct tier.

    :param queue_url: A single queue's url
    :param deploy_stage: The specified deployment environment (DEV, TEST, QA, PROD-EXTERNAL)
    :param region: typically 'us-west-2'
    :return: is_iow_queue: is this an IOW queue or not
    :rtype: bool
    """
    sqs_client = boto3.client("sqs", region_name=region)

    is_iow_queue = False

    # filtering on deploy tier, which we capitalize
    if deploy_stage.upper() in queue_url:
        # launch API call to grab the tags for the queue
        queue_tags = sqs_client.list_queue_tags(QueueUrl=queue_url)

        # we only want queues that are tagged as 'IOW'
        if 'Tags' in queue_tags:
            if 'wma:organization' in queue_tags['Tags']:
                if 'IOW' == queue_tags['Tags']['wma:organization']:
                    is_iow_queue = True

    return is_iow_queue
