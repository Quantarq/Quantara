"""
This module contains text messages used in the Telegram bot.
Supports i18n helper for EN and ES locales.
"""

TEXTS = {
    "en": {
        "WELCOME_MESSAGE": (
            "Quantara allows you to earn by using ETH collateral, "
            "borrowing USDC, and compounding the process. You can get started "
            "right away by clicking the button below to launch the web app! 🚀👇"
        ),
        "HEALTH_RATIO_WARNING_MESSAGE": (
            "⚠️ Warning: Your health ratio level is {health_ratio}. "
            "This is getting low - please add more deposit to avoid liquidation.\n\n"
            "Visit quantara.xyz to manage your position."
        ),
        "NOTIFICATION_ALLOWED_MESSAGE": (
            "You have successfully allowed notifications! "
            "You will now receive updates and alerts regarding your account. "
            "Thank you for staying connected with us! 🎉"
        )
    },
    "es": {
        "WELCOME_MESSAGE": (
            "Quantara le permite ganar usando garantía de ETH, "
            "pidiendo prestado USDC y componiendo el proceso. ¡Puede comenzar "
            "de inmediato haciendo clic en el botón de abajo para iniciar la aplicación web! 🚀👇"
        ),
        "HEALTH_RATIO_WARNING_MESSAGE": (
            "⚠️ Advertencia: Su nivel de ratio de salud es {health_ratio}. "
            "Esto se está reduciendo - por favor, agregue más depósito para evitar la liquidación.\n\n"
            "Visite quantara.xyz para administrar su posición."
        ),
        "NOTIFICATION_ALLOWED_MESSAGE": (
            "¡Ha permitido las notificaciones con éxito! "
            "Ahora recibirá actualizaciones y alertas sobre su cuenta. "
            "¡Gracias por mantenerse conectado con nosotros! 🎉"
        )
    }
}

class I18nHelper:
    """
    Helper class for managing internationalization (i18n) of texts.
    """
    def __init__(self, default_lang="en"):
        """
        Initializes the I18nHelper with a default language.
        """
        self.default_lang = default_lang

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Retrieves a translated text by key, optionally formatted with kwargs.
        """
        lang = lang or self.default_lang
        if lang not in TEXTS:
            lang = self.default_lang
        text = TEXTS[lang].get(key, TEXTS[self.default_lang].get(key, key))
        if kwargs:
            return text.format(**kwargs)
        return text

i18n = I18nHelper()
