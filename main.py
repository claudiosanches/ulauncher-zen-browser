import re
import logging
from typing import List, Optional

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
    SystemExitEvent,
)
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from zenbrowser import ZenBrowserDatabase

logger = logging.getLogger(__name__)


class ZenBrowserExtension(Extension):
    """Zen Browser extension for Ulauncher."""

    def __init__(self):
        super().__init__()
        self.database = ZenBrowserDatabase()

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(SystemExitEvent, SystemExitEventListener())


class PreferencesEventListener(EventListener):
    """Handles initial preference loading."""

    def on_event(self, event: PreferencesEvent, extension: ZenBrowserExtension):
        extension.database.order = event.preferences.get("order")
        extension.database.search_type = event.preferences.get("search_type", "both")
        try:
            extension.database.limit = int(event.preferences.get("limit", 5))
        except (ValueError, TypeError):
            extension.database.limit = 5
            logger.warning("Invalid limit preference provided, defaulting to 5.")


class PreferencesUpdateEventListener(EventListener):
    """Handles real-time preference updates."""

    def on_event(self, event: PreferencesUpdateEvent, extension: ZenBrowserExtension):
        if event.id == "order":
            extension.database.order = event.new_value
        elif event.id == "search_type":
            extension.database.search_type = event.new_value
        elif event.id == "limit":
            try:
                extension.database.limit = int(event.new_value)
            except (ValueError, TypeError):
                logger.warning(f"Invalid limit value updated: {event.new_value}")


class SystemExitEventListener(EventListener):
    """Handles extension shutdown."""

    def on_event(self, _: SystemExitEvent, extension: ZenBrowserExtension):
        extension.database.close()


class KeywordQueryEventListener(EventListener):
    """Handles keyword queries from Ulauncher."""

    DOMAIN_REGEX = re.compile(
        r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}(/.*)?$', re.IGNORECASE
    )

    def on_event(self, event: KeywordQueryEvent, extension: ZenBrowserExtension) -> RenderResultListAction:
        # Strip ensures leading/trailing spaces don't break detection
        query: str = (event.get_argument() or "").strip()

        if not query:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/icon.svg",
                    name="Zen Browser Search",
                    description="Search bookmarks/history or type a URL",
                    highlightable=False,
                )
            ])

        items: List[ExtensionResultItem] = []

        # URL detection
        url_to_open: Optional[str] = None

        # 1. Explicit protocol (triggers as soon as http:// etc. is typed)
        if re.match(r'^(?:http|ftp)s?://', query, re.IGNORECASE):
            url_to_open = query
        # 2. Domain-like structure (e.g. google.com or www.google.com)
        elif self.DOMAIN_REGEX.match(query) or query.lower().startswith("www."):
            url_to_open = query if query.lower().startswith(("http://", "https://")) else f"https://{query}"

        if url_to_open:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.svg",
                    name="Open URL",
                    description=url_to_open,
                    highlightable=False,
                    on_enter=OpenUrlAction(url_to_open),
                )
            )

        # Database search
        results = extension.database.search(query)
        for url, label, _ in results:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.svg",
                    name=label,
                    description=url,
                    highlightable=False,
                    on_enter=OpenUrlAction(url),
                )
            )

        return RenderResultListAction(items)


if __name__ == "__main__":
    ZenBrowserExtension().run()
