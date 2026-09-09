import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    property string label: ""
    property string value: ""
    property color statusColor: Theme.colorSuccess
    property bool dotVisible: true
    property bool pulse: false

    implicitHeight: 28
    implicitWidth: pillRow.implicitWidth + Theme.spacingMd * 2

    color: Theme.colorObsidian
    border.color: Theme.colorBorder
    border.width: 1
    radius: Theme.radiusPill

    RowLayout {
        id: pillRow
        anchors.centerIn: parent
        spacing: Theme.spacingSm

        Rectangle {
            id: statusDot
            visible: root.dotVisible
            width: 8
            height: 8
            radius: 4
            color: root.statusColor

            SequentialAnimation on opacity {
                running: root.pulse
                loops: Animation.Infinite
                NumberAnimation { from: 1.0; to: 0.3; duration: 800; easing.type: Easing.InOutQuad }
                NumberAnimation { from: 0.3; to: 1.0; duration: 800; easing.type: Easing.InOutQuad }
            }
        }

        Text {
            text: root.label
            visible: root.label.length > 0
            font.family: Theme.fontSans
            font.pixelSize: Theme.fontSizeCaption
            font.weight: Font.Medium
            color: Theme.textSecondary
        }

        Text {
            text: root.value
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSizeCaption
            font.weight: Font.Bold
            color: Theme.textPrimary
        }
    }
}
