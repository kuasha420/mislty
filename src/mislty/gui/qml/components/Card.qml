import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    default property alias content: contentArea.data
    property string title: ""
    property string subtitle: ""
    property color headerColor: Theme.textPrimary
    property bool hoverable: false
    property alias contentLayout: contentArea

    color: (hoverable && mouseArea.containsMouse) ? Theme.colorCardHover : Theme.colorCard
    border.color: (hoverable && mouseArea.containsMouse) ? Theme.colorBorderHighlight : Theme.colorBorder
    border.width: 1
    radius: Theme.radiusMd

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.hoverable
        hoverEnabled: root.hoverable
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            visible: root.title.length > 0
            spacing: Theme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: root.title
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeH3
                    font.weight: Font.DemiBold
                    color: root.headerColor
                }

                Text {
                    text: root.subtitle
                    visible: root.subtitle.length > 0
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeCaption
                    color: Theme.textSecondary
                }
            }
        }

        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
