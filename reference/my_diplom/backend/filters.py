from django_filters import rest_framework as filters

from backend.models import Order


class OrderFilter(filters.FilterSet):
    """ Фильтр для Заказов
        по клиенту и по датам.
    """
    # Можно выбрать конкретную дату создания: '?created_date=2024-08-02'.
    created_date = filters.DateFilter(field_name='created_at', lookup_expr='date')

    # Можно выбрать интервал дат создания: '?created_after=2024-07-20&created_before=2024-08-03'.
    created = filters.DateFromToRangeFilter(field_name="created_at", lookup_expr='date')
    created_after = filters.DateFromToRangeFilter(field_name="created", lookup_expr='gte')
    created_before = filters.DateFromToRangeFilter(field_name="created", lookup_expr='lte')

    # Можно выбрать конкретную дату обновления: '?updated_date=2024-08-02'.
    updated_date = filters.DateFilter(field_name='updated_state', lookup_expr='date')

    # Можно выбрать интервал дат обновления: '?updated_after=2024-07-20&updated_before=2024-08-03'.
    updated = filters.DateFromToRangeFilter(field_name="updated_state", lookup_expr='date')
    updated_after = filters.DateFromToRangeFilter(field_name="updated", lookup_expr='gte')
    updated_before = filters.DateFromToRangeFilter(field_name="updated", lookup_expr='lte')

    class Meta:
        model = Order
        fields = ['customer']    # Можно выбрать какого-нибудь пользователя.
