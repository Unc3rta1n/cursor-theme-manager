pragma Singleton
import QtQuick

QtObject {
    readonly property SystemPalette palette: SystemPalette { colorGroup: SystemPalette.Active }
    readonly property color accent: palette.highlight
    readonly property color muted: Qt.alpha(palette.windowText, 0.6)
    readonly property color urgent: "#f28b82"
    readonly property var popups: ({
        background: palette.window,
        text: palette.windowText,
        border: Qt.alpha(palette.windowText, 0.2)
    })
}
