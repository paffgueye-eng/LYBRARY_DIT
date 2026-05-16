from rest_framework.routers import DefaultRouter
from .views import LoanViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'', LoanViewSet, basename='loan')
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    *router.urls,
]
