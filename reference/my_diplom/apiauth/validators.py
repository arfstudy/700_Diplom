def validate_required_fields(incoming_data, fields):
    """ Проверяет присутствие обязательных полей и наличие записей в них.
    """
    errors = {}
    data_keys = incoming_data.keys()
    for field in fields:
        if field not in data_keys:
            errors[field] = ['Отсутствует обязательное поле.']
        else:
            if incoming_data[field] == "":
                errors[field] = ['Данное поле не может быть пустым.']
            elif incoming_data[field].replace(" ", "") == "":
                errors[field] = ['Данное поле не может состоять из одних пробелов.']

    return errors
