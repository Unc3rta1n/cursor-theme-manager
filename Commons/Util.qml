pragma Singleton
import QtQuick

QtObject {
    function alpha(value: color, opacity: real): color { return Qt.alpha(value, opacity); }
}
