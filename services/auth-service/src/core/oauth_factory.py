from core.config import settings
from core.oauth_client import YandexOAuthProvider


class OAuthProviderFactory:
    _providers = {}

    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, provider_name: str):
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Получаем настройки из конфига
        provider_config = settings.oauth_providers.get(provider_name)
        if not provider_config:
            raise ValueError(f"Provider {provider_name} not configured")

        return cls._providers[provider_name](
            client_id=provider_config.client_id,
            client_secret=provider_config.client_secret,
            redirect_uri=provider_config.redirect_uri
        )


OAuthProviderFactory.register_provider("yandex", YandexOAuthProvider)
