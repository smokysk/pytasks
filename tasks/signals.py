from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from tasks.models import Task
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from tasks.utils import notify_task

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler.start()

def schedule_notification(instance):
    job_id = f"notification_{instance.pk}"
    run_date = instance.deadline - timedelta(hours=1)

    job = scheduler.get_job(job_id)
    if job:
        job.modify(next_run_time=run_date)
    else:
        scheduler.add_job(
            notify_task,
            'date',
            run_date=run_date,
            id=job_id,
            replace_existing=True,
            args=[instance.pk]
        )

@receiver(post_save, sender=Task)
def schedule_and_notify(sender, instance, **kwargs):
    schedule_notification(instance)
