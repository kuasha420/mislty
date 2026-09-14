pragma Singleton
import QtQuick

QtObject {
    id: theme

    // --- Obsidian & Titanium Color Tokens ---
    // Void / Canvas backgrounds
    readonly property color colorVoid: "#080a0f"
    readonly property color colorObsidian: "#0d1017"
    readonly property color colorCard: "#121622"
    readonly property color colorCardHover: "#171c2b"
    readonly property color colorRaised: "#1b2133"
    readonly property color colorInput: "#0a0d14"
    readonly property color colorOverlay: "#d8080a0f"

    // Border & Divider tokens
    readonly property color colorBorder: "#1e2638"
    readonly property color colorBorderSubtle: Qt.rgba(255, 255, 255, 0.06)
    readonly property color colorBorderHighlight: "#2d3752"
    readonly property color colorBorderActive: "#38bdf8"

    // Brand & Accent tokens
    readonly property color colorCyan: "#38bdf8"       // Titanium Sky Cyan
    readonly property color colorGold: "#f59e0b"       // Warm Honey Amber
    readonly property color colorPurple: "#a855f7"     // Electric Violet
    readonly property color colorCoral: "#fb7185"

    // Gradients & Surfaces
    readonly property color gradientHeroStart: "#00e5ff"       // Vibrant Electric Cyan
    readonly property color gradientHeroEnd: "#0077b6"         // Deep Radiant Blue
    readonly property color gradientDangerStart: "#e11d48"     // Refined Rose/Crimson
    readonly property color gradientDangerEnd: "#9f1239"       // Deep Crimson
    readonly property color gradientWarnStart: "#d97706"       // Warm Amber
    readonly property color gradientWarnEnd: "#b45309"         // Deep Amber
    readonly property color gradientSuccessStart: "#10b981"    // Emerald
    readonly property color gradientSuccessEnd: "#047857"      // Deep Emerald
    readonly property color gradientCardTop: "#141926"
    readonly property color gradientCardBottom: "#101420"

    // Input Surface tokens
    readonly property color colorInputBorder: "#1e2638"
    readonly property color colorInputFocus: "#38bdf8"

    // Semantic Status tokens
    readonly property color colorSuccess: "#10b981"    // Refined Emerald
    readonly property color colorWarning: "#f59e0b"    // Refined Amber
    readonly property color colorDanger: "#f43f5e"     // Refined Rose
    readonly property color colorInfo: "#38bdf8"
    readonly property color colorCrimson: "#f43f5e"
    readonly property color colorEmerald: "#10b981"
    readonly property color colorCyanMuted: Qt.rgba(56, 189, 248, 0.20)

    // Foreground / Text tokens
    readonly property color textPrimary: "#f8fafc"
    readonly property color textSecondary: "#94a3b8"
    readonly property color textMuted: "#64748b"
    readonly property color textInverse: "#080a0f"

    // --- Typography ---
    readonly property string fontSans: "Inter, Cantarell, Ubuntu, DejaVu Sans, Noto Sans, Segoe UI, sans-serif"
    readonly property string fontMono: "JetBrains Mono, Fira Code, DejaVu Sans Mono, Noto Sans Mono, Consolas, monospace"

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
    readonly property int radiusXs: 4
    readonly property int radiusSm: 6
    readonly property int radiusMd: 10
    readonly property int radiusLg: 18
    readonly property int radiusXl: 24
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
