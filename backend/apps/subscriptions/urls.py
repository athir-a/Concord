from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_root_view = False
router.register("subscriptions", views.SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls
