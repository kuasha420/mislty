import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    signal clicked()

    property string text: ""
    property string loadingText: ""
    property string iconName: ""
    property string iconGlyph: ""
    property string variant: "primary"  // "primary", "secondary", "danger", "gold", "warning", "success", "outline", "ghost"
    property bool disabled: false
    property bool loading: false
    property int buttonRadius: Theme.radiusPill

    implicitHeight: 38
    implicitWidth: (text.length > 0) ? Math.max(96, btnRow.implicitWidth + Theme.spacingLg * 2) : implicitHeight
    radius: buttonRadius
    scale: (!disabled && !loading && mouseArea.pressed) ? 0.98 : 1.0

    Behavior on scale { NumberAnimation { duration: 80 } }

    function resolvedIconName() {
        if (iconName.length > 0) return iconName;
        if (iconGlyph === "▶") return "play";
        if (iconGlyph === "⏹") return "square";
        if (iconGlyph === "⟳" || iconGlyph === "🔄") return "refresh-cw";
        if (iconGlyph === "🔌") return "plug";
        if (iconGlyph === "💾") return "copy";
        if (iconGlyph === "⚡") return "zap";
        if (iconGlyph === "🔍") return "search";
        if (iconGlyph === "📡") return "radio";
        if (iconGlyph === "🌐") return "globe";
        if (iconGlyph === "✏️" || iconGlyph === "✎") return "edit";
        if (iconGlyph === "➤" || iconGlyph === "📤") return "send";
        if (iconGlyph === "📞" || iconGlyph === "📱") return "phone";
        if (iconGlyph === "🗑️" || iconGlyph === "🗑") return "trash";
        if (iconGlyph === "📖") return "book-open";
        if (iconGlyph === "⚠️") return "alert-triangle";
        return "";
    }

    readonly property bool isGradient: !disabled && (variant === "primary" || variant === "danger" || variant === "gold" || variant === "warning" || variant === "success")

    gradient: isGradient ? btnGradient : null

    Gradient {
        id: btnGradient
        orientation: Gradient.Horizontal
        GradientStop {
            position: 0.0
            color: {
                if (root.variant === "primary") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientHeroStart, 1.08) : Theme.gradientHeroStart;
                if (root.variant === "danger") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientDangerStart, 1.08) : Theme.gradientDangerStart;
                if (root.variant === "gold" || root.variant === "warning") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientWarnStart, 1.08) : Theme.gradientWarnStart;
                if (root.variant === "success") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientSuccessStart, 1.08) : Theme.gradientSuccessStart;
                return Theme.gradientHeroStart;
            }
        }
        GradientStop {
            position: 1.0
            color: {
                if (root.variant === "primary") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientHeroEnd, 1.08) : Theme.gradientHeroEnd;
                if (root.variant === "danger") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientDangerEnd, 1.08) : Theme.gradientDangerEnd;
                if (root.variant === "gold" || root.variant === "warning") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientWarnEnd, 1.08) : Theme.gradientWarnEnd;
                if (root.variant === "success") return mouseArea.containsMouse ? Qt.lighter(Theme.gradientSuccessEnd, 1.08) : Theme.gradientSuccessEnd;
                return Theme.gradientHeroEnd;
            }
        }
    }

    color: {
        if (root.isGradient) return "transparent";
        if (disabled) return "#182232";
        if (variant === "secondary") return mouseArea.containsMouse ? "#1e2c44" : "#162032";
        if (variant === "outline") return mouseArea.containsMouse ? Qt.rgba(56, 189, 248, 0.12) : "transparent";
        if (variant === "ghost") return mouseArea.containsMouse ? Qt.rgba(255, 255, 255, 0.08) : "transparent";
        return "#162032";
    }

    border.color: {
        if (disabled) return Theme.colorBorder;
        if (variant === "secondary") return mouseArea.containsMouse ? "#3b82f6" : "#243048";
        if (variant === "outline") return mouseArea.containsMouse ? Theme.colorCyan : "#243048";
        return "transparent";
    }
    border.width: (variant === "outline" || variant === "secondary" || disabled) ? 1 : 0

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: !root.disabled && !root.loading
        hoverEnabled: true
        cursorShape: root.loading ? Qt.BusyCursor : (root.disabled ? Qt.ArrowCursor : Qt.PointingHandCursor)
        onClicked: root.clicked()
    }

    RowLayout {
        id: btnRow
        anchors.centerIn: parent
        spacing: Theme.spacingSm

        // Normal Icon
        Icon {
            id: vectorIcon
            visible: root.resolvedIconName().length > 0 && !root.loading
            name: root.resolvedIconName()
            size: 15
            color: root.disabled ? Theme.textMuted : "#ffffff"
        }

        // Animated Loading Spinner
        Item {
            id: spinnerContainer
            visible: root.loading
            width: 15
            height: 15

            Icon {
                id: spinnerIcon
                anchors.centerIn: parent
                name: "refresh-cw"
                size: 15
                color: root.disabled ? Theme.textMuted : "#ffffff"
            }

            RotationAnimator {
                target: spinnerContainer
                from: 0
                to: 360
                duration: 800
                loops: Animation.Infinite
                running: root.loading
            }
        }

        Text {
            visible: displayText.length > 0
            readonly property string displayText: {
                if (root.loading && root.loadingText.length > 0) return root.loadingText;
                return root.text;
            }
            text: displayText
            font.family: Theme.fontSans
            font.pixelSize: Theme.fontSizeBody
            font.weight: Font.DemiBold
            color: root.disabled ? Theme.textMuted : (root.variant === "outline" ? Theme.colorCyan : "#ffffff")
        }
    }
}
