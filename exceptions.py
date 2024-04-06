class TokensIsNoneException(Exception):
    """Токен отсутствует."""
    pass


class TelegramErrorException(Exception):
    """Ошибка со стороны телеграма."""
    pass


class IncorrectResponseCodeException(Exception):
    """Неправильный код ответа."""
    pass
