import datetime
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):

    def generate_upload_path(self, instance):
        upload_path = "uploads/{}/{}".format(
            str(self.user.id).lower(), instance
        )
        return upload_path

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    enabled = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    token = models.CharField(max_length=200, blank=True)
    qr_code_url = models.CharField(max_length=200, blank=True)
    qr_code = models.ImageField(upload_to=generate_upload_path, blank=True, null=True)
    created_date = models.DateTimeField("created", default=timezone.now)
    last_updated = models.DateTimeField("last updated", default=timezone.now)

    def __str__(self):
        return f"{self.id} - {self.user.username}"

    def was_created_recently(self):
        return self.created_date >= timezone.now() - datetime.timedelta(days=1)

    def reset_mfa(self):
        return self.last_updated + datetime.timedelta(days=1) <= timezone.now()

    def save(self, *args, **kwargs):
        # Refresh update timestamp
        self.last_updated = timezone.now()
        # Save
        super().save(*args, **kwargs)
