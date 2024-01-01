from celery import shared_task
from celery.utils.log import get_task_logger
from . import extract_task_and_date, send_task_to_drf_api, get_tasks_data, format_tasks_response

logger = get_task_logger(__name__)

@shared_task
def celery_extract_task_and_date(context_args):
    return extract_task_and_date(context_args)

@shared_task
def celery_send_task_to_drf_api(api_url, payload, headers):
    return send_task_to_drf_api(api_url, payload, headers)

@shared_task
def celery_get_tasks_data(api_url, params, headers):
    return get_tasks_data(api_url, params, headers)

@shared_task
def celery_format_tasks_response(tasks_data):
    return format_tasks_response(tasks_data)
