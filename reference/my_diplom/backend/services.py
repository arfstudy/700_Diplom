from rest_framework.exceptions import NotFound

from backend.models import Contact


def get_contacts(user, pk=0):
    """ Возвращает контакты пользователя из БД.
    """
    if pk == 0:
        return Contact.objects.filter(salesman__id=user.id)

    contact = Contact.objects.filter(salesman__id=user.id).filter(pk=pk)
    if not contact:
        raise NotFound(f'У Вас нет контакта с id={pk}.')

    return contact


def get_transmitted_obj(obj_ser, obj_fields):
    """ Возвращает объект заданного класса, реальный или абстрактный с пустыми значениями.
    """
    obj = None
    action = obj_ser.context['view'].action
    if action == 'create':
        obj_data = {e: 'None' for e in obj_fields}
        obj = obj_ser.Meta.model(**obj_data)
    elif action in ['update', 'partial_update']:
        obj = obj_ser.instance

    return action, obj
