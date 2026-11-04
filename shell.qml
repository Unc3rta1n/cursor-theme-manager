//@ pragma Env QS_NO_RELOAD_POPUP=1
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic
//@ pragma Env CTM_STANDALONE=1
import QtQuick
import Quickshell
import Quickshell.Io

ShellRoot {
    id: host

    function summon(pluginId: string, payload: string): void { panel.open(payload); }
    function hide(pluginId: string): void { panel.close(); }

    CursorService {
        id: cursorService
        shell: host
        manifest: ({ id: "sanjyay.cursor-theme-manager", __sourceDir: Quickshell.shellPath("") })
    }

    Panel {
        id: panel
        shell: host
        service: cursorService
    }

    Component.onCompleted: {
        if (Quickshell.env("CTM_START_HIDDEN") !== "1")
            panel.open("{}");
    }

    IpcHandler {
        target: "manager"
        function open(): void { panel.open("{}"); }
        function hide(): void { panel.close(); }
        function quit(): void { Qt.quit(); }
        function status(): string {
            return JSON.stringify({ready: cursorService.ready, visible: panel.opened, themes: cursorService.themes.length,
                error: cursorService.lastError, theme: cursorService.committedTheme, size: cursorService.committedSize});
        }
    }
}
