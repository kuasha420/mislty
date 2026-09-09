import QtQuick
import QtQuick.Layouts
import ".."

Item {
    id: root

    property int bars: 0             // 0 to 5
    property int csq: 0              // 0 to 31 or 99
    property int dbm: -113           // in dBm
    property bool showText: true
    property color barColor: Theme.signalColor(root.csq)

    implicitWidth: barRow.implicitWidth + (showText ? textColumn.implicitWidth + Theme.spacingSm : 0)
    implicitHeight: 32

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacingSm

        Row {
            id: barRow
            spacing: 3
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: 5
                Rectangle {
                    required property int index
                    width: 4
                    height: 8 + (index * 4)   // 8, 12, 16, 20, 24 px
                    anchors.bottom: parent.bottom
                    radius: 1
                    color: (index < root.bars) ? root.barColor : Theme.colorRaised
                    opacity: (index < root.bars) ? 1.0 : 0.4

                    Behavior on color { ColorAnimation { duration: Theme.animFast } }
                    Behavior on opacity { NumberAnimation { duration: Theme.animFast } }
                }
            }
        }

        ColumnLayout {
            id: textColumn
            visible: root.showText
            spacing: 1
            Layout.alignment: Qt.AlignVCenter

            Text {
                text: (root.bars > 0) ? (root.bars + "/5 BARS") : "NO SIGNAL"
                font.family: Theme.fontSans
                font.pixelSize: Theme.fontSizeCaption
                font.weight: Font.Bold
                color: root.bars > 0 ? Theme.textPrimary : Theme.colorDanger
            }

            Text {
                text: (root.csq > 0 && root.csq !== 99) ? (root.csq + " CSQ (" + root.dbm + " dBm)") : "Disconnected"
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.textSecondary
            }
        }
    }
}
