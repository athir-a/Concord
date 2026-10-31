from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_root_view = False
router.register("tax-rules", views.TaxRuleViewSet)
router.register("products", views.ProductViewSet)
router.register("plans", views.PlanViewSet)
router.register("discount-rules", views.DiscountRuleViewSet)
router.register("quotation-templates", views.QuotationTemplateViewSet)

urlpatterns = router.urls
