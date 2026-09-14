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

        // ===================================================================
        // TOP CARD: HARDWARE & SERIAL PORT INSPECTOR
        // ===================================================================
        Card {
            Layout.fillWidth: true
            title: "Modem Hardware & Serial Endpoints"
            subtitle: (bridge?.modemPresent ?? false) ? "Physical USB peripheral nodes in /dev/mislty/" : "No Qualcomm MDM9600 hardware detected on USB bus"
            iconName: "cpu"
            iconColor: Theme.colorCyan

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                // Unplugged Warning Banner
                Rectangle {
                    visible: !(bridge?.modemPresent ?? false)
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusMd
                    color: Qt.rgba(243, 156, 18, 0.12)
                    border.color: Theme.colorGold
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacingMd
                        anchors.rightMargin: Theme.spacingMd
                        spacing: Theme.spacingSm

                        Icon { name: "alert-triangle"; size: 14; color: Theme.colorGold }
                        Text {
                            Layout.fillWidth: true
                            text: "Hardware Unplugged: Connect the USB modem to activate AT serial control and diagnostics."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            font.weight: Font.DemiBold
                            color: Theme.colorGold
                        }
                    }
                }

                // Port Status Pills Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    StatusPill {
                        label: "CONTROL"
                        value: (bridge?.hardwarePorts?.control) ? bridge.hardwarePorts.control : "MISSING"
                        statusColor: (bridge?.hardwarePorts?.control) ? Theme.colorSuccess : Theme.colorDanger
                    }

                    StatusPill {
                        label: "DATA"
                        value: (bridge?.hardwarePorts?.data) ? bridge.hardwarePorts.data : "MISSING"
                        statusColor: (bridge?.hardwarePorts?.data) ? Theme.colorSuccess : Theme.colorDanger
                    }

                    StatusPill {
                        label: "VOICE"
                        value: (bridge?.hardwarePorts?.voice) ? bridge.hardwarePorts.voice : "OFFLINE"
                        statusColor: (bridge?.hardwarePorts?.voice) ? Theme.colorSuccess : Theme.textMuted
                    }

                    StatusPill {
                        label: "DIAG"
                        value: (bridge?.hardwarePorts?.diag) ? bridge.hardwarePorts.diag : "OFFLINE"
                        statusColor: (bridge?.hardwarePorts?.diag) ? Theme.colorSuccess : Theme.textMuted
                    }

                    Item { Layout.fillWidth: true }

                    StatusPill {
                        label: "USB BUS"
                        value: (bridge?.modemPresent ?? false) ? ((bridge?.hardwarePorts?.vid ?? "05c6") + ":" + (bridge?.hardwarePorts?.pid ?? "9025")) : "UNPLUGGED"
                        statusColor: (bridge?.modemPresent ?? false) ? Theme.colorSuccess : Theme.colorDanger
                    }
                }
            }
        }

        // ===================================================================
        // BOTTOM CARD: AT DIAGNOSTIC TERMINAL
        // ===================================================================
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "AT Diagnostic Terminal"
            subtitle: (bridge?.modemReady ?? false) ? "Direct serial port transaction console" : "Console standby — serial port offline"
            iconName: "terminal"
            iconColor: Theme.colorCyan

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spacingMd

                // Console Output
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusMd
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
                            text: {
                                if (!(bridge?.modemPresent ?? false)) {
                                    return root.consoleLog + "\n[SYSTEM] Modem hardware is disconnected. Please connect the USB modem to send AT commands.";
                                }
                                return root.consoleLog;
                            }
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
                        model: ["AT+CSQ", "AT+COPS?", "AT+CEREG?", "AT+CPIN?", "AT+CGMI", "AT$MYWIFI?"]
                        FelineButton {
                            required property string modelData
                            text: modelData
                            variant: "outline"
                            disabled: !(bridge?.modemReady ?? false)
                            implicitHeight: 26
                            implicitWidth: 78
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
                        iconName: "trash"
                        implicitHeight: 26
                        implicitWidth: 74
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
                        radius: Theme.radiusMd
                        color: Theme.colorObsidian
                        border.color: atInput.activeFocus ? Theme.colorCyan : Theme.colorBorder
                        border.width: 1

                        TextInput {
                            id: atInput
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSm
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeBody
                            color: Theme.textPrimary
                            selectByMouse: true
                            enabled: bridge?.modemReady ?? false
                            // Placeholder
                            Text {
                                text: (bridge?.modemReady ?? false) ? "Enter AT command (e.g. AT+CSQ)..." : "Modem disconnected — AT terminal unavailable..."
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
                        iconName: "zap"
                        implicitWidth: 104
                        implicitHeight: 38
                        disabled: !(bridge?.modemReady ?? false) || !atInput.text
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
