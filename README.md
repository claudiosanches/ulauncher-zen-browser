# Ulauncher Zen Browser Launcher

![screenshot](images/screenshot.png)

Simple [Ulauncher](https://ulauncher.io) extension for opening websites in Zen Browser. The extension provides suggestions
based on the browsing history as well as the bookmarks.

## Features

- Search through Zen Browser history and bookmarks.
- Supports both local (`~/.zen`) and Flatpak (`~/.var/app/app.zen_browser/.zen`) installations.
- Highly customizable results ordering.

## Settings

In Ulauncher GUI, you can set the extension's preferences. Here, the **maximal number** of suggested items and the
respective **sorting criteria** can be changed. The order of suggestions can be determined by:

- **Last visit date**: Most recently visited pages first.
- **Visit count**: Most frequently visited pages first.
- **Zen Browser frecency**: Uses the [Mozilla Frecency algorithm](https://developer.mozilla.org/en-US/docs/Mozilla/Tech/Places/Frecency_algorithm) to rank results.

## Usage

Open Ulauncher and type in the set up keyword (defaults to `zen`). You can then either provide a valid URL to open a
webpage, or a search query to browse your browser's history and bookmarks.

To open the selected URL, press **Enter**. You can also copy the URL to your input by pressing **ALT + ENTER**.

## Troubleshooting

If the extension cannot find your Zen Browser data, ensure it is installed in one of the following locations:
- `~/.zen/`
- `~/.var/app/app.zen_browser.zen/.zen/`

The extension expects a `profiles.ini` file in these directories to locate your browsing data.

## Credits

This project is based on and inspired by the [Ulauncher Firefox Launcher](https://github.com/freisatz/ulauncher-firefox-launcher/) by freisatz.

## License

This project is licensed under the terms of the GPLv3 license. See the LICENSE file for details.
