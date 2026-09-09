import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property int activeThreadId: -1
    property string activeRecipient: ""

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXl
        spacing: Theme.spacingLg

        // Left Pane: SMS Threads / Ingest
        Card {
            Layout.fillHeight: true
            Layout.preferredWidth: 320
            title: "SMS Conversations"
            subtitle: "Indexed in local SQLite"

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    FelineButton {
                        Layout.fillWidth: true
                        text: "Sync SIM SMS"
                        variant: "gold"
                        iconGlyph: "🔄"
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.syncSms();
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // Threads placeholder / list
                ListView {
                    id: threadsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: bridge?.smsThreads ?? []

                    delegate: Rectangle {
                        required property var modelData
                        width: threadsList.width
                        height: 54
                        radius: Theme.radiusSm
                        color: (modelData.id === root.activeThreadId) ? Theme.colorCardHover : "transparent"
                        border.color: (modelData.id === root.activeThreadId) ? Theme.colorCyan : "transparent"
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                root.activeThreadId = modelData.id;
                                root.activeRecipient = modelData.phone_number;
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.getSmsMessages(modelData.id);
                                }
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.phone_number
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: modelData.updated_at ? modelData.updated_at.substring(11, 16) : ""
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textMuted
                                }
                            }

                            Text {
                                text: modelData.last_message ? modelData.last_message : "..."
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Empty state
                    Text {
                        anchors.centerIn: parent
                        visible: threadsList.count === 0
                        text: "No conversation threads yet.\nClick 'Sync SIM SMS' to ingest."
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeCaption
                        color: Theme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        // Right Pane: Message Viewer & Composer
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: root.activeRecipient.length > 0 ? ("Thread: " + root.activeRecipient) : "SMS Composer"
            subtitle: "GSM-7 text messaging"

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingMd

                // Messages scroll area
                ListView {
                    id: messagesList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: bridge?.smsMessages ?? []

                    delegate: RowLayout {
                        required property var modelData
                        width: messagesList.width
                        spacing: Theme.spacingSm

                        Item {
                            visible: modelData.direction === "OUT"
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            implicitWidth: Math.min(messagesList.width * 0.75, msgText.implicitWidth + Theme.spacingLg * 2)
                            implicitHeight: msgText.implicitHeight + Theme.spacingMd * 2
                            radius: Theme.radiusMd
                            color: modelData.direction === "OUT" ? Qt.rgba(0, 240, 255, 0.15) : Theme.colorObsidian
                            border.color: modelData.direction === "OUT" ? Theme.colorCyan : Theme.colorBorder
                            border.width: 1

                            Text {
                                id: msgText
                                anchors.fill: parent
                                anchors.margins: Theme.spacingMd
                                text: modelData.body
                                wrapMode: Text.Wrap
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textPrimary
                            }
                        }

                        Item {
                            visible: modelData.direction !== "OUT"
                            Layout.fillWidth: true
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: messagesList.count === 0
                        text: "Select a conversation or compose a new SMS message below."
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeCaption
                        color: Theme.textMuted
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.colorBorder
                }

                // Compose Box
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Rectangle {
                        width: 180
                        height: 38
                        radius: Theme.radiusSm
                        color: Theme.colorObsidian
                        border.color: Theme.colorBorder
                        border.width: 1

                        TextInput {
                            id: recipientInput
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            text: root.activeRecipient
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeBody
                            color: Theme.textPrimary
                            selectByMouse: true
                            // Placeholder
                            Text {
                                text: "+8801XXXXXXXXX"
                                visible: !recipientInput.text
                                color: Theme.textMuted
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 38
                        radius: Theme.radiusSm
                        color: Theme.colorObsidian
                        border.color: Theme.colorBorder
                        border.width: 1

                        TextInput {
                            id: msgInput
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeBody
                            color: Theme.textPrimary
                            selectByMouse: true
                            // Placeholder
                            Text {
                                text: "Type text message..."
                                visible: !msgInput.text
                                color: Theme.textMuted
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeBody
                            }
                        }
                    }

                    FelineButton {
                        text: "Send"
                        variant: "primary"
                        iconGlyph: "➤"
                        implicitWidth: 90
                        implicitHeight: 38
                        disabled: !recipientInput.text || !msgInput.text
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                var ok = bridge.sendSms(recipientInput.text, msgInput.text);
                                if (ok) {
                                    msgInput.text = "";
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
