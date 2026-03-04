"""Контекст-процесори для шаблонів."""


def current_url_name(request):
    """Додає в контекст current_url_name для безпечного підсвічування поточної вкладки."""
    url_name = ""
    if getattr(request, "resolver_match", None) is not None:
        url_name = getattr(request.resolver_match, "url_name", "") or ""
    return {"current_url_name": url_name}
