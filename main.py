import re
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    ItemEnterEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
    SystemExitEvent,
)
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from zenbrowser import ZenBrowserDatabase


class ZenBrowserExtension(Extension):

    def __init__(self):
        super(ZenBrowserExtension, self).__init__()

        #   Zen Browser database object
        self.database = ZenBrowserDatabase()

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(SystemExitEvent, SystemExitEventListener())


class PreferencesEventListener(EventListener):

    def on_event(self, event: PreferencesEvent, extension: ZenBrowserExtension):
        extension.database.order = event.preferences["order"]
        extension.database.limit = event.preferences["limit"]


class PreferencesUpdateEventListener(EventListener):

    def on_event(self, event: PreferencesUpdateEvent, extension: ZenBrowserExtension):
        if event.id == "order":
            extension.database.order = event.new_value
        elif event.id == "limit":
            extension.database.limit = event.new_value


class SystemExitEventListener(EventListener):

    def on_event(self, _: SystemExitEvent, extension: ZenBrowserExtension):
        extension.database.close()


class KeywordQueryEventListener(EventListener):

    def on_event(self, event: KeywordQueryEvent, extension: ZenBrowserExtension):
        query = event.get_argument() or ""

        #   Empty query
        if not query:
            return RenderResultListAction(
                [
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name="Zen Browser Search",
                        description="Search bookmarks/history or type a URL",
                        highlightable=False,
                    )
                ]
            )

        items = []

        #   Check if query is a URL
        is_url = False
        url_to_open = query
        if re.match(r'^(?:http|ftp)s?://', query, re.IGNORECASE):
            is_url = True
        elif re.match(r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}(/.*)?$', query, re.IGNORECASE):
            is_url = True
            if not query.startswith(('http://', 'https://')):
                url_to_open = 'https://' + query

        if is_url:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="Open URL",
                    description=url_to_open,
                    highlightable=False,
                    on_enter=OpenUrlAction(url_to_open),
                )
            )

        #   Search Zen Browser bookmarks and history
        results = extension.database.search(query)

        for row in results:
            url = row[0]
            label = row[1]
            is_bookmark = row[2]

            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=label,
                    description=url,
                    highlightable=False,
                    on_enter=OpenUrlAction(url),
                )
            )

        return RenderResultListAction(items)


if __name__ == "__main__":
    ZenBrowserExtension().run()
