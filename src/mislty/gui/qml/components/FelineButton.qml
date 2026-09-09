import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    signal clicked()

    property string text: "Button"
    property string iconGlyph: ""
    property string variant: "primary"  // "primary", "secondary", "danger", "gold", "outline"
    property bool disabled: false
    property bool loading: false

    implicitHeight: 36
    implicitWidth: Math.max(100, btnRow.implicitWidth + Theme.spacingLg * 2)
    radius: Theme.radiusMd

    function getBaseColor() {
        if (disabled) return Theme.colorRaised;
        if (variant === "primary") return Theme.colorCyan;
        if (variant === "gold") return Theme.colorGold;
        if (variant === "danger") return Theme.colorDanger;
        if (variant === "secondary") return Theme.colorObsidian;
        if (variant === "outline") return "transparent";
        return Theme.colorCyan;
    }

    function getTextColor() {
        if (disabled) return Theme.textMuted;
        if (variant === "primary" || variant === "gold") return Theme.textInverse;
        if (variant === "danger") return "#ffffff";
        if (variant === "secondary") return Theme.textPrimary;
        if (variant === "outline") return Theme.colorCyan;
        return Theme.textInverse;
    }

    color: {
        var base = getBaseColor();
        if (disabled || variant === "outline") return base;
        if (mouseArea.pressed) return Qt.darker(base, 1.2);
        if (mouseArea.containsMouse) return Qt.lighter(base, 1.15);
        return base;
    }

    border.color: {
        if (disabled) return Theme.colorBorder;
        if (variant === "outline") return mouseArea.containsMouse ? Theme.colorCyan : Theme.colorBorderHighlight;
        if (variant === "secondary") return mouseArea.containsMouse ? Theme.colorCyan : Theme.colorBorder;
        return "transparent";
    }
    border.width: (variant === "outline" || variant === "secondary") ? 1 : 0

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: !root.disabled && !root.loading
        hoverEnabled: true
        cursorShape: (root.disabled || root.loading) ? Qt.ArrowCursor : Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    RowLayout {
        id: btnRow
        anchors.centerIn: parent
        spacing: Theme.spacingSm

        Text {
            text: root.iconGlyph
            visible: root.iconGlyph.length > 0 && !root.loading
            font.family: Theme.fontSans
            font.pixelSize: Theme.fontSizeBody
            color: root.getTextColor()
        }

        Text {
            id: spinner
            text: "⟳"
            visible: root.loading
            font.pixelSize: Theme.fontSizeBody
            color: root.getTextColor()
            RotationAnimator {
                target: spinner
                from: 0
                to: 360
                duration: 900
                loops: Animation.Infinite
                running: root.loading
            }
        }

        Text {
            text: root.text
            font.family: Theme.fontSans
            font.pixelSize: Theme.fontSizeBody
            font.weight: Font.DemiBold
            color: root.getTextColor()
        }
    }
}
