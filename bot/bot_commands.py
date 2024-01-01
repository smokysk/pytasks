import os
import requests
from datetime import datetime
from typing import Optional
from django.http import JsonResponse
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import ContextTypes

from tasks.models import Task
from tasks.utils import notify_task

headers = {
    'Authorization': f'Bearer {os.getenv("JWT_TOKEN")}',
}

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler.start()

async def extract_task_and_date(context_args):
    if len(context_args) < 2:
        raise ValueError("Please provide both task description and date with time. Example: /addtask Buy groceries 2023-01-01 15:30")

    date_with_time = ' '.join(context_args[-2:])

    try:
        task = ' '.join(context_args[:-2])
        deadline = datetime.strptime(date_with_time, "%Y-%m-%d %H:%M")
        return task, deadline
    except ValueError:
        raise ValueError("Invalid format. Please use: /add_task Buy groceries 2023-01-01 15:30")

async def send_task_to_drf_api(api_url, payload, headers):
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return True, "Task added successfully!"
    except requests.RequestException as e:
        return False, f"Failed to add task. Error: {str(e)}"

async def get_tasks_data(api_url, params, headers):
    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to retrieve tasks. Error: {str(e)}")

async def format_tasks_response(tasks_data):
    if tasks_data:
        task_list = "\n".join([f"ID: {task['id']} - {task['task_name']} - Deadline: {task['deadline'][0:10]} {task['deadline'][11:-4]}" for task in tasks_data])
        return f"Unfinished tasks:\n{task_list}"
    else:
        return "No tasks found."

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task, deadline = await extract_task_and_date(context.args)

        api_url = os.getenv('DRF_API_URL')
        if not api_url:
            await update.message.reply_text("DRF_API_URL is not configured.")
            return

        payload = {
            'task_name': task,
            'deadline': deadline.isoformat(),
            'user': update.effective_user.id,
        }

        success, response_message = await send_task_to_drf_api(api_url, payload, headers)
        await update.message.reply_text(response_message) if success else await update.message.reply_text(response_message)

    except ValueError as ve:
        await update.message.reply_text(str(ve))

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_url = os.getenv('DRF_API_URL')
    if not api_url:
        await update.message.reply_text("DRF_API_URL is not configured.")
        return

    params = {'user': update.effective_user.id}

    try:
        tasks_data = await get_tasks_data(api_url, params, headers)
        response_message = await format_tasks_response(tasks_data)
        await update.message.reply_text(response_message)
    except Exception as e:
        await update.message.reply_text(str(e))

async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    params = {'user': update.effective_user.id}
    task_id = context.args[0]
    api_url = f"{os.getenv('DRF_API_URL')}{task_id}/"

    if not api_url:
        await update.message.reply_text("DRF_API_URL is not configured.")
        return

    try:
        response = requests.get(api_url, params=params, headers=headers)
        task_data = response.json()
    except requests.RequestException as e:
        await update.message.reply_text(f"Failed to retrieve tasks. Error: {str(e)}")

    try:
        task = f"ID: {task_data['id']} - {task_data['task_name']} - Deadline: {task_data['deadline'][0:10]} {task_data['deadline'][11:-4]} {'\U00002705' if task_data['finished'] else '\U0000274C'}"
        await update.message.reply_text(str(task))
    except KeyError:
        await update.message.reply_text('No task found.')

async def update_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id, new_name, new_date = await extract_update_task_params(context.args)
        api_url = f"{os.getenv('DRF_API_URL')}{task_id}/"
        
        if not api_url:
            await update.message.reply_text("DRF_API_URL is not configured.")
            return

        data = {'user': update.effective_user.id, "task_name": new_name, "deadline": new_date}
        success, response_message = await send_update_task_to_drf_api(api_url, data, headers)
        await update.message.reply_text(response_message) if success else await update.message.reply_text(response_message)

    except ValueError as ve:
        await update.message.reply_text(str(ve))

async def finish_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = context.args[0]
        api_url = f"{os.getenv('DRF_API_URL')}{task_id}/"

        if not api_url:
            await update.message.reply_text("DRF_API_URL is not configured.")
            return

        success, response_message = await send_finish_task_to_drf_api(api_url, headers)
        await update.message.reply_text(response_message) if success else await update.message.reply_text(response_message)

    except ValueError as ve:
        await update.message.reply_text(str(ve))

async def extract_update_task_params(args) -> Optional[tuple]:
    if len(args) < 3:
        raise ValueError("Please provide task ID, new description, and new deadline. Example: /update_task 1 Buy groceries 2023-01-01 15:30")

    try:
        task_id = int(args[0])
        new_name = ' '.join(args[1:-2])
        new_date = ' '.join(args[-2:])
        return task_id, new_name, new_date
    except (ValueError, TypeError):
        raise ValueError("Invalid task ID. Please provide a valid numeric task ID.")

async def send_update_task_to_drf_api(api_url, data, headers):
    try:
        response = requests.put(api_url, json=data, headers=headers)
        response.raise_for_status()

        if 'detail' in response.json():
            raise ValueError('Permission denied.')

        return True, "Task updated successfully!"

    except requests.RequestException as e:
        return False, f"Failed to update task. Error: {str(e)}"

async def send_finish_task_to_drf_api(api_url, headers):
    try:
        response = requests.delete(api_url, headers=headers)
        response.raise_for_status()

        data = response.json()

        if 'detail' in data:
            raise ValueError('Permission denied.')

        if data.get('finished', False):
            return True, 'Task completed successfully.'
        else:
            return True, 'Task uncompleted successfully.'

    except requests.RequestException as e:
        return False, f"Failed to finish task. Error: {str(e)}"
