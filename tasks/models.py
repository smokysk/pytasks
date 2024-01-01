from django.db import models
from datetime import datetime


class Task(models.Model):
    id = models.BigAutoField(
        null=False,
        primary_key=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        null=True,
    )
    task_name = models.CharField(
        max_length=200
    )
    deadline = models.DateTimeField(
        default=datetime.today(),
        blank=False
    )
    user = models.IntegerField()
    finished = models.BooleanField(
        default=False
    )
    
    def __str__(self):
        return self.task_name
    
    class Meta:
        managed = True
        db_table = 'task'

