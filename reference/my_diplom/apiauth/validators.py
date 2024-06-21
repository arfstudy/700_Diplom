def validate_incoming_fields(incoming_data, fields):
    """ Проверяет присутствие заданных полей и наличие записей в них.
    """
    status = True
    errors = {}
    data_keys = incoming_data.keys()
    for field in fields:
        if field not in data_keys:
            status = False
            errors[field] = 'Отсутствует обязательное поле.'
        else:
            if incoming_data[field] == "":
                status = False
                errors[field] = 'Данное поле не может быть пустым.'
            elif incoming_data[field].replace(" ", "") == "":
                status = False
                errors[field] = 'Данное поле не может состоять из одних пробелов.'

    return errors, status
