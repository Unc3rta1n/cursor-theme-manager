pragma Singleton
import QtQuick

QtObject {
    readonly property real cornerRadius: 12
    readonly property real normalBorderWidth: 1
    readonly property real hoverBorderWidth: 1
    readonly property real selectedBorderWidth: 2
    readonly property var font: ({
        family: "sans-serif",
        caption: 11, bodySmall: 12, body: 14, title: 18, displayLarge: 28
    })

    function space(value: real): real { return value; }
    function normalFillFor(text: color, accent: color): color { return Qt.alpha(text, 0.04); }
    function hoverFillFor(text: color, accent: color): color { return Qt.alpha(accent, 0.12); }
    function selectedFillFor(text: color, accent: color): color { return Qt.alpha(accent, 0.2); }
    function normalBorderFor(text: color, accent: color): color { return Qt.alpha(text, 0.16); }
    function hoverBorderFor(text: color, accent: color): color { return Qt.alpha(accent, 0.6); }
    function selectedBorderFor(text: color, accent: color): color { return accent; }
}
