import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

Item {
    id: root

    property string direction: "IN"      // "IN" or "OUT"
    property string body: ""
    property var timestamp: 0            // Float epoch seconds or string
    property string status: "DELIVERED"  // "SENT", "DELIVERED", "RECEIVED", "FAILED"
    property string senderNumber: ""

    readonly property bool isOutgoing: direction.toUpperCase() === "OUT"
    readonly property bool isFailed: status.toUpperCase() === "FAILED"

    implicitWidth: parent ? parent.width : 400
    implicitHeight: bubbleContainer.height + Theme.spacingSm

    // Formatted timestamp (HH:MM or string representation)
    function formatTime(ts) {
        if (!ts) return "";
        if (typeof ts === "number") {
            var date = new Date(ts * 1000);
            var h = date.getHours();
            var m = date.getMinutes();
            return (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m);
        }
        if (typeof ts === "string") {
            if (ts.length >= 16) {
                return ts.substring(11, 16);
            }
            return ts;
        }
        return "";
    }

    RowLayout {
        id: bubbleContainer
        width: root.width
        spacing: 0

        // Push outgoing bubbles to the right
        Item {
            visible: root.isOutgoing
            Layout.fillWidth: true
        }

        Rectangle {
            id: bubbleCard
            Layout.maximumWidth: Math.min(root.width * 0.78, 520)
            Layout.minimumWidth: Math.min(root.width * 0.4, 200)
            implicitHeight: contentCol.implicitHeight + Theme.spacingMd * 2
            implicitWidth: Math.max(contentCol.implicitWidth + Theme.spacingLg * 2, 180)

            radius: Theme.radiusMd
            color: root.isOutgoing ? Qt.rgba(0, 240, 255, 0.08) : Theme.colorCardHover
            border.color: root.isOutgoing
                          ? (root.isFailed ? Theme.colorCrimson : Qt.rgba(0, 240, 255, 0.35))
                          : Theme.colorBorder
            border.width: 1

            ColumnLayout {
                id: contentCol
                anchors.fill: parent
                anchors.margins: Theme.spacingMd
                spacing: Theme.spacingSm

                // Text body
                TextEdit {
                    id: messageText
                    Layout.fillWidth: true
                    text: root.body
                    wrapMode: Text.Wrap
                    readOnly: true
                    selectByMouse: true
                    color: Theme.textPrimary
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeBody
                    selectionColor: Theme.colorCyanMuted
                    selectedTextColor: "#ffffff"
                }

                // Metadata Footer Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    // Timestamp
                    Text {
                        text: root.formatTime(root.timestamp)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.textMuted
                    }

                    // Status Pill / Badge
                    Rectangle {
                        visible: root.isOutgoing
                        implicitHeight: 16
                        implicitWidth: statusText.implicitWidth + 8
                        radius: 8
                        color: root.isFailed ? Qt.rgba(255, 51, 102, 0.2) : Qt.rgba(0, 240, 255, 0.15)

                        Text {
                            id: statusText
                            anchors.centerIn: parent
                            text: root.isFailed ? "FAILED" : (root.status.toUpperCase() === "DELIVERED" ? "✓✓ DELIVERED" : "✓ SENT")
                            font.family: Theme.fontMono
                            font.pixelSize: 9
                            font.weight: Font.Bold
                            color: root.isFailed ? Theme.colorCrimson : Theme.colorCyan
                        }
                    }

                    Item { Layout.fillWidth: true }

                    // Copy feedback label
                    Text {
                        id: copyFeedback
                        visible: false
                        text: "Copied!"
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeSmall
                        font.weight: Font.Bold
                        color: Theme.colorEmerald

                        Timer {
                            id: feedbackTimer
                            interval: 1500
                            onTriggered: copyFeedback.visible = false
                        }
                    }

                    // Copy action button
                    Rectangle {
                        width: 22
                        height: 22
                        radius: 4
                        color: copyHover.containsMouse ? Theme.colorSurface : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "📋"
                            font.pixelSize: 11
                            opacity: copyHover.containsMouse ? 1.0 : 0.6
                        }

                        MouseArea {
                            id: copyHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge && bridge.copyToClipboard) {
                                    bridge.copyToClipboard(root.body);
                                }
                                copyFeedback.visible = true;
                                feedbackTimer.restart();
                            }
                        }
                    }
                }
            }
        }

        // Push incoming bubbles to the left
        Item {
            visible: !root.isOutgoing
            Layout.fillWidth: true
        }
    }
}
