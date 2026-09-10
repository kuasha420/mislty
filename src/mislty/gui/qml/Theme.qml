pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- Feline Color Tokens ---
    // Void / Obsidian backgrounds
    readonly property color colorVoid: "#0c0e14"
    readonly property color colorObsidian: "#141721"
    readonly property color colorCard: "#181c2b"
    readonly property color colorCardHover: "#202538"
    readonly property color colorRaised: "#252b40"
    readonly property color colorOverlay: "#cc0c0e14"

    // Border & Divider tokens
    readonly property color colorBorder: "#1f2438"
    readonly property color colorBorderHighlight: "#2f3856"
    readonly property color colorBorderActive: "#00f0ff"

    // Brand & Accent tokens
    readonly property color colorCyan: "#00f0ff"       // Terminal Cyan
    readonly property color colorGold: "#f39c12"       // Feline Purr Gold
    readonly property color colorPurple: "#9b5de5"     // Feline Lavender
    readonly property color colorCoral: "#ff6f61"

    // Semantic Status tokens
    readonly property color colorSuccess: "#00e676"    // Online / Signal Good
    readonly property color colorWarning: "#ffb300"    // Warning / Medium Signal
    readonly property color colorDanger: "#ff3366"     // Error / Disconnected / Weak
    readonly property color colorInfo: "#00b4d8"
    readonly property color colorCrimson: "#ff3366"
    readonly property color colorEmerald: "#00e676"
    readonly property color colorCyanMuted: Qt.rgba(0, 240, 255, 0.35)

    // Foreground / Text tokens
    readonly property color textPrimary: "#f0f6fc"
    readonly property color textSecondary: "#8b949e"
    readonly property color textMuted: "#565d6d"
    readonly property color textInverse: "#0c0e14"

    // --- Typography ---
    readonly property string fontSans: "Inter, Cantarell, Ubuntu, DejaVu Sans, Segoe UI, sans-serif"
    readonly property string fontMono: "JetBrains Mono, Fira Code, DejaVu Sans Mono, Consolas, monospace"

    readonly property int fontSizeH1: 22
    readonly property int fontSizeH2: 17
    readonly property int fontSizeH3: 14
    readonly property int fontSizeBody: 13
    readonly property int fontSizeCaption: 11
    readonly property int fontSizeSmall: 10
    readonly property int fontSizeMono: 12

    // --- Spacing Scale (4px base) ---
    readonly property int spacingXxs: 2
    readonly property int spacingXs: 4
    readonly property int spacingSm: 8
    readonly property int spacingMd: 12
    readonly property int spacingLg: 16
    readonly property int spacingXl: 24
    readonly property int spacingXxl: 32

    // --- Corner Radii ---
    readonly property int radiusSm: 4
    readonly property int radiusMd: 8
    readonly property int radiusLg: 12
    readonly property int radiusXl: 16
    readonly property int radiusPill: 999

    // --- Animation Timings ---
    readonly property int animFast: 150
    readonly property int animNormal: 250
    readonly property int animSlow: 400

    // --- Helper Functions ---
    function formatBytes(bytes) {
        if (!bytes || bytes <= 0) return "0 B";
        var b = Number(bytes);
        if (b < 1024) return b + " B";
        var kb = b / 1024;
        if (kb < 1024) return kb.toFixed(1) + " KB";
        var mb = kb / 1024;
        if (mb < 1024) return mb.toFixed(2) + " MB";
        var gb = mb / 1024;
        return gb.toFixed(2) + " GB";
    }

    function formatRate(bytesPerSec) {
        if (!bytesPerSec || bytesPerSec <= 0) return "0 B/s";
        var r = Number(bytesPerSec);
        if (r < 1024) return r.toFixed(0) + " B/s";
        var kb = r / 1024;
        if (kb < 1024) return kb.toFixed(1) + " KB/s";
        var mb = kb / 1024;
        return mb.toFixed(2) + " MB/s";
    }

    function csqToDbm(csq) {
        if (csq === undefined || csq === null || csq < 0 || csq === 99) return "N/A";
        return (-113 + (csq * 2)) + " dBm";
    }

    function csqToBars(csq) {
        if (!csq || csq <= 0 || csq === 99) return 0;
        if (csq >= 22) return 5;
        if (csq >= 17) return 4;
        if (csq >= 12) return 3;
        if (csq >= 7)  return 2;
        return 1;
    }

    function signalColor(csq) {
        var bars = csqToBars(csq);
        if (bars >= 4) return colorSuccess;
        if (bars === 3) return colorCyan;
        if (bars === 2) return colorWarning;
        return colorDanger;
    }

    function durationString(seconds) {
        if (!seconds || seconds <= 0) return "00:00:00";
        var s = Math.floor(seconds);
        var hrs = Math.floor(s / 3600);
        var mins = Math.floor((s % 3600) / 60);
        var secs = s % 60;
        var p = function(n) { return (n < 10 ? "0" : "") + n; };
        return p(hrs) + ":" + p(mins) + ":" + p(secs);
    }
}
