import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    default property alias content: contentArea.data
    property string title: ""
    property string subtitle: ""
    property string iconName: ""
    property color iconColor: Theme.colorCyan
    property color headerColor: Theme.textPrimary
    property bool hoverable: false
    property Component headerAction: null
    property alias contentLayout: contentArea

    gradient: Gradient {
        GradientStop { position: 0.0; color: (hoverable && mouseArea.containsMouse) ? Theme.colorCardHover : Theme.gradientCardTop }
        GradientStop { position: 1.0; color: (hoverable && mouseArea.containsMouse) ? Theme.colorCard : Theme.gradientCardBottom }
    }
    border.color: (hoverable && mouseArea.containsMouse) ? Theme.colorBorderHighlight : Theme.colorBorder
    border.width: 1
    radius: Theme.radiusLg

    implicitWidth: 240
    Layout.minimumWidth: 200
    implicitHeight: cardColumn.implicitHeight + (Theme.spacingLg * 2)

    Behavior on color { ColorAnimation { duration: Theme.animFast } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFast } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.hoverable
        hoverEnabled: root.hoverable
    }

    ColumnLayout {
        id: cardColumn
        anchors.fill: parent
        anchors.margins: Theme.spacingLg
        spacing: Theme.spacingMd

        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            visible: root.title.length > 0
            spacing: Theme.spacingSm

            Rectangle {
                visible: root.iconName.length > 0
                width: 28
                height: 28
                radius: Theme.radiusSm
                color: Qt.rgba(root.iconColor.r, root.iconColor.g, root.iconColor.b, 0.12)
                border.color: Qt.rgba(root.iconColor.r, root.iconColor.g, root.iconColor.b, 0.25)
                border.width: 1

                Icon {
                    anchors.centerIn: parent
                    name: root.iconName
                    size: 15
                    color: root.iconColor
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Text {
                    text: root.title
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeH3
                    font.weight: Font.DemiBold
                    color: root.headerColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: root.subtitle
                    visible: root.subtitle.length > 0
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeCaption
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Loader {
                id: actionLoader
                sourceComponent: root.headerAction
                visible: root.headerAction !== null
                Layout.alignment: Qt.AlignVCenter
            }
        }

        ColumnLayout {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingMd
        }
    }
}
