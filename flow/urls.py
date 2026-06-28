from django.urls import path

from . import views


app_name = "flow"

urlpatterns = [
    path("", views.Index.as_view(), name="index"),
    path("profile/", views.Profile.as_view(), name="profile"),
    path("update/", views.UpdateUser.as_view(), name="update"),
    path("health/", views.Health.as_view(), name="health"),
    path("logout/", views.Logout.as_view(), name="logout"),
]
