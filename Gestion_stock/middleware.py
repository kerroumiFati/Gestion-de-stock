"""
Custom middleware for handling user language preferences
"""
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class UserLanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set the language based on user's SystemConfig preference.
    This middleware should run after AuthenticationMiddleware and LocaleMiddleware.
    """

    def process_request(self, request):
        language_to_activate = 'fr'  # Default fallback

        if request.user.is_authenticated:
            try:
                from API.models import SystemConfig
                config = SystemConfig.get_solo()

                logger.info(f"UserLanguageMiddleware: User {request.user.username} authenticated")
                logger.info(f"UserLanguageMiddleware: Config exists: {config is not None}")

                if config and config.language:
                    logger.info(f"UserLanguageMiddleware: Config language: {config.language}")

                    # Validate the language code
                    if config.language in ['fr', 'en', 'ar']:
                        language_to_activate = config.language
                    else:
                        logger.warning(f"UserLanguageMiddleware: Invalid language code: {config.language}")
                else:
                    logger.info("UserLanguageMiddleware: No language set in config")

            except Exception as e:
                # If there's any error, just use the default language
                logger.error(f"UserLanguageMiddleware error: {e}", exc_info=True)

        # Activate the language
        translation.activate(language_to_activate)
        request.LANGUAGE_CODE = language_to_activate
        logger.info(f"UserLanguageMiddleware: Activated language: {language_to_activate}")
