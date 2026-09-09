import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXl
        spacing: Theme.spacingLg

        // Wi-Fi Radio Controller Hero Card
        Card {
            Layout.fillWidth: true
            implicitHeight: 120
            title: "Broadcom Wi-Fi Hotspot Radio"
            subtitle: "Co-processor 802.11b/g/n softAP"

            RowLayout {
                anchors.fill: parent
                spacing: Theme.spacingXl

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: (bridge?.wifiPower ?? false) ? "Wi-Fi Radio: BROADCASTING" : "Wi-Fi Radio: OFF"
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeH2
                        font.weight: Font.Bold
                        color: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted
                    }

                    Text {
                        text: (bridge?.wifiPower ?? false) ? ("SSID: " + ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "Active")) : "Radio is in low-power shutdown state."
                        font.family: Theme.fontSans
                        font.pixelSize: Theme.fontSizeBody
                        color: Theme.textSecondary
                    }
                }

                FelineButton {
                    text: (bridge?.wifiPower ?? false) ? "Power Off Wi-Fi" : "Power On Wi-Fi"
                    variant: (bridge?.wifiPower ?? false) ? "danger" : "gold"
                    iconGlyph: "📶"
                    implicitWidth: 160
                    implicitHeight: 44
                    onClicked: {
                        if (typeof bridge !== "undefined" && bridge) {
                            bridge.toggleWifi();
                        }
                    }
                }
            }
        }

        // Wi-Fi Credentials & Configuration
        Card {
            Layout.fillWidth: true
            implicitHeight: 180
            title: "Access Point Credentials"
            subtitle: "Configure custom SSID and WPA2 security key"

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingLg

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingXs

                        Text { text: "NETWORK NAME (SSID)"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textSecondary }
                        Rectangle {
                            Layout.fillWidth: true
                            height: 36
                            radius: Theme.radiusSm
                            color: Theme.colorObsidian
                            border.color: Theme.colorBorder
                            border.width: 1

                            TextInput {
                                id: ssidInput
                                anchors.fill: parent
                                anchors.margins: Theme.spacingSm
                                text: (bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "MisLTy-420"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textPrimary
                                selectByMouse: true
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingXs

                        Text { text: "WPA2 PASSPHRASE"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textSecondary }
                        Rectangle {
                            Layout.fillWidth: true
                            height: 36
                            radius: Theme.radiusSm
                            color: Theme.colorObsidian
                            border.color: Theme.colorBorder
                            border.width: 1

                            TextInput {
                                id: passInput
                                anchors.fill: parent
                                anchors.margins: Theme.spacingSm
                                text: "12345678"
                                echoMode: TextInput.Password
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeBody
                                color: Theme.textPrimary
                                selectByMouse: true
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    FelineButton {
                        text: "Apply Credentials"
                        variant: "primary"
                        iconGlyph: "💾"
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.setWifiCredentials(ssidInput.text, passInput.text);
                            }
                        }
                    }
                }
            }
        }

        // Connected Clients Card
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Connected Client Stations"
            subtitle: "Devices associated to this AP"

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingSm

                Text {
                    text: (bridge?.wifiClientsCount ?? 0) > 0 ? ((bridge?.wifiClientsCount ?? 0) + " client station(s) connected") : "No wireless clients currently connected."
                    font.family: Theme.fontSans
                    font.pixelSize: Theme.fontSizeBody
                    color: (bridge?.wifiClientsCount ?? 0) > 0 ? Theme.colorCyan : Theme.textMuted
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
