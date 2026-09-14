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

    implicitHeight: 26
    implicitWidth: pillRow.implicitWidth + Theme.spacingMd * 2

    color: Qt.rgba(root.statusColor.r, root.statusColor.g, root.statusColor.b, 0.08)
    border.color: Qt.rgba(root.statusColor.r, root.statusColor.g, root.statusColor.b, 0.24)
    border.width: 1
    radius: Theme.radiusPill

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    RowLayout {
        id: pillRow
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            id: statusDot
            visible: root.dotVisible
            width: 6
            height: 6
            radius: 3
            color: root.statusColor

            SequentialAnimation on opacity {
                running: root.pulse
                loops: Animation.Infinite
                NumberAnimation { from: 1.0; to: 0.3; duration: 900; easing.type: Easing.InOutQuad }
                NumberAnimation { from: 0.3; to: 1.0; duration: 900; easing.type: Easing.InOutQuad }
            }
        }

        Text {
            text: root.label
            visible: root.label.length > 0
            font.family: Theme.fontSans
            font.pixelSize: Theme.fontSizeSmall
            font.weight: Font.DemiBold
            color: Theme.textMuted
        }

        Text {
            text: root.value
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSizeSmall
            font.weight: Font.Bold
            color: Theme.textPrimary
        }
    }
}
