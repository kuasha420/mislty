import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property string consoleLog: "MisLTy Diagnostic Terminal initialized.\nEnter raw AT commands below.\n"

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingMd

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "AT Diagnostic Terminal & Hardware Inspector"
            subtitle: "Direct serial port transaction console"

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingMd

                // Console Output
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.colorVoid
                    border.color: Theme.colorBorder
                    border.width: 1

                    ScrollView {
                        id: scrollView
                        anchors.fill: parent
                        anchors.margins: Theme.spacingSm
                        clip: true

                        TextArea {
                            id: logArea
                            readOnly: true
                            text: root.consoleLog
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeMono
                            color: Theme.colorCyan
                            background: null
                            selectByMouse: true
                            wrapMode: Text.Wrap
                        }
                    }
                }

                // Quick Shortcuts Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Text {
                        text: "QUICK:"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.textMuted
                    }

                    Repeater {
                        model: ["AT+CSQ", "AT+COPS?", "AT+CPIN?", "AT+CGMI", "AT$MYWIFI?"]
                        FelineButton {
                            required property string modelData
                            text: modelData
                            variant: "outline"
                            implicitHeight: 26
                            implicitWidth: 72
                            onClicked: {
                                atInput.text = modelData;
                                sendCommand(modelData);
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    FelineButton {
                        text: "Clear"
                        variant: "secondary"
                        implicitHeight: 26
                        implicitWidth: 60
                        onClicked: {
                            root.consoleLog = "";
                        }
                    }
                }

                // Command Input Box
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Rectangle {
                        Layout.fillWidth: true
                        height: 38
                        radius: Theme.radiusSm
                        color: Theme.colorObsidian
                        border.color: Theme.colorBorder
                        border.width: 1

                        TextInput {
                            id: atInput
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeBody
                            color: Theme.textPrimary
                            selectByMouse: true
                            // Placeholder
                            Text {
                                text: "Enter AT command (e.g. AT+CSQ)..."
                                visible: !atInput.text
                                color: Theme.textMuted
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                            }
                            onAccepted: sendCommand(atInput.text)
                        }
                    }

                    FelineButton {
                        text: "Execute"
                        variant: "primary"
                        iconGlyph: "⚡"
                        implicitWidth: 96
                        implicitHeight: 38
                        disabled: !atInput.text
                        onClicked: sendCommand(atInput.text)
                    }
                }
            }
        }
    }

    function sendCommand(cmd) {
        if (!cmd) return;
        var cleanCmd = cmd.trim();
        root.consoleLog += "\n> " + cleanCmd + "\n";
        var resp = "";
        if (typeof bridge !== "undefined" && bridge) {
            resp = bridge.executeAt(cleanCmd);
        }
        root.consoleLog += (resp ? resp : "<No response>") + "\n";
        atInput.text = "";
    }
}
