import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property bool showPassword: false

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: Theme.spacingLg

            // ===============================================================
            // TOP HERO CARD: WI-FI RADIO CONTROLLER & DUAL-PLANE STATE
            // ===============================================================
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 110
                radius: Theme.radiusLg
                color: Theme.colorObsidian
                border.color: (bridge?.wifiPower ?? false) ? Theme.colorBorderActive : Theme.colorBorder
                border.width: (bridge?.wifiPower ?? false) ? 1.5 : 1

                Behavior on border.color { ColorAnimation { duration: Theme.animNormal } }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingLg
                    spacing: Theme.spacingXl

                    // Radio Icon Tile
                    Rectangle {
                        width: 56
                        height: 56
                        radius: Theme.radiusMd
                        color: (bridge?.wifiPower ?? false) ? Qt.rgba(0, 240, 255, 0.12) : Qt.rgba(121, 130, 169, 0.12)
                        border.color: (bridge?.wifiPower ?? false) ? Theme.colorCyan : Theme.colorBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: (bridge?.wifiPower ?? false) ? "📶" : "💤"
                            font.pixelSize: 26
                        }
                    }

                    // Radio Metadata
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        RowLayout {
                            spacing: Theme.spacingSm

                            Text {
                                text: (bridge?.wifiPower ?? false) ? "Broadcom 802.11b/g/n: ACTIVE" : "Broadcom Wi-Fi Radio: STANDBY"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeH2
                                font.weight: Font.Bold
                                color: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted
                            }

                            Rectangle {
                                height: 20
                                width: modeTag.implicitWidth + 12
                                radius: Theme.radiusSm
                                color: Qt.rgba(0, 240, 255, 0.1)
                                border.color: Qt.rgba(0, 240, 255, 0.3)
                                border.width: 1

                                Text {
                                    id: modeTag
                                    anchors.centerIn: parent
                                    text: ((bridge?.operationalMode ?? "usb_modem") === "pocket_router") ? "POCKET ROUTER" : "USB MODEM + AUX AP"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    font.weight: Font.Bold
                                    color: Theme.colorCyan
                                }
                            }
                        }

                        Text {
                            text: (bridge?.wifiPower ?? false)
                                ? ("Broadcasting clean SSID '" + ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "Active") + "' • Channel 11 • 2.4 GHz")
                                : "Radio powered down into low-power sleep mode (commit to NVRAM)."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.textSecondary
                        }
                    }

                    // Radio Power Toggle Action
                    FelineButton {
                        text: (bridge?.wifiPower ?? false) ? "Power Off Radio" : "Power On Radio"
                        variant: (bridge?.wifiPower ?? false) ? "danger" : "gold"
                        iconGlyph: "⚡"
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

            // ===============================================================
            // SMART MODE SWITCHER (USB CELLULAR VS POCKET ROUTER)
            // ===============================================================
            Card {
                Layout.fillWidth: true
                title: "Smart Operational Mode Switcher"
                subtitle: "Sub-4s seamless handover between Host USB Modem and Standalone Pocket Router"

                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingXl

                    // USB Modem Mode Card Option
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: Theme.radiusMd
                        color: ((bridge?.operationalMode ?? "usb_modem") === "usb_modem") ? Theme.colorCardHover : Theme.colorObsidian
                        border.color: ((bridge?.operationalMode ?? "usb_modem") === "usb_modem") ? Theme.colorCyan : Theme.colorBorder
                        border.width: ((bridge?.operationalMode ?? "usb_modem") === "usb_modem") ? 1.5 : 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.switchMode("usb_modem");
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingMd
                            spacing: Theme.spacingMd

                            Text { text: "💻"; font.pixelSize: 24 }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: "USB Cellular Modem Mode"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: ((bridge?.operationalMode ?? "usb_modem") === "usb_modem") ? Theme.colorCyan : Theme.textPrimary
                                }
                                Text {
                                    text: "Host direct ppp0 dialup • 57.9ms ultra-low latency • Full Linux desktop integration"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }

                    // Pocket Router Mode Card Option
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: Theme.radiusMd
                        color: ((bridge?.operationalMode ?? "usb_modem") === "pocket_router") ? Theme.colorCardHover : Theme.colorObsidian
                        border.color: ((bridge?.operationalMode ?? "usb_modem") === "pocket_router") ? Theme.colorGold : Theme.colorBorder
                        border.width: ((bridge?.operationalMode ?? "usb_modem") === "pocket_router") ? 1.5 : 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.switchMode("pocket_router");
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spacingMd
                            spacing: Theme.spacingMd

                            Text { text: "🌐"; font.pixelSize: 24 }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: "Pocket Wi-Fi Router Mode"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: ((bridge?.operationalMode ?? "usb_modem") === "pocket_router") ? Theme.colorGold : Theme.textPrimary
                                }
                                Text {
                                    text: "Autonomous baseband routing • 192.168.100.1 softAP • Multi-client station hotspot"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }
                }
            }

            // ===============================================================
            // WI-FI CREDENTIALS & HARDWARE AP CONFIGURATION
            // ===============================================================
            Card {
                Layout.fillWidth: true
                title: "Access Point Credentials & NVRAM Commit"
                subtitle: "Writes clean un-suffixed SSID via embedded GoForm API (no manufacturer MAC tail)"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        // SSID Input
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Text { text: "NETWORK NAME (CLEAN SSID)"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textSecondary }
                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                TextInput {
                                    id: ssidInput
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingSm
                                    text: (bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "TypeScript 420"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textPrimary
                                    selectByMouse: true
                                }
                            }
                        }

                        // Passphrase Input
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Text { text: "WPA2-PSK PASSPHRASE"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textSecondary }
                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingSm
                                    spacing: Theme.spacingSm

                                    TextInput {
                                        id: passInput
                                        Layout.fillWidth: true
                                        text: "12345678"
                                        echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeBody
                                        color: Theme.textPrimary
                                        selectByMouse: true
                                    }

                                    Text {
                                        text: root.showPassword ? "🙈" : "👁"
                                        font.pixelSize: 16
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.showPassword = !root.showPassword
                                        }
                                    }
                                }
                            }
                        }

                        // Channel Selector
                        ColumnLayout {
                            width: 140
                            spacing: Theme.spacingXs

                            Text { text: "CHANNEL"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textSecondary }
                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                ComboBox {
                                    id: channelBox
                                    anchors.fill: parent
                                    model: ["Channel 11 (2462 MHz)", "Channel 6 (2437 MHz)", "Channel 1 (2412 MHz)", "Channel 0 (Auto)"]
                                    currentIndex: 0
                                    background: null
                                }
                            }
                        }
                    }

                    // Save / Apply Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        FelineButton {
                            text: "Open Web UI (192.168.100.1)"
                            variant: "outline"
                            iconGlyph: "🌐"
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.openWebUi();
                                }
                            }
                        }

                        FelineButton {
                            text: "Reboot Modem Hardware"
                            variant: "secondary"
                            iconGlyph: "🔄"
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.rebootModem();
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        FelineButton {
                            text: "Apply Credentials"
                            variant: "primary"
                            iconGlyph: "💾"
                            implicitWidth: 160
                            implicitHeight: 38
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    var ch = 11;
                                    if (channelBox.currentIndex === 1) ch = 6;
                                    else if (channelBox.currentIndex === 2) ch = 1;
                                    else if (channelBox.currentIndex === 3) ch = 0;
                                    bridge.saveWifiConfig(ssidInput.text, passInput.text, ch);
                                }
                            }
                        }
                    }
                }
            }

            // ===============================================================
            // LIVE CONNECTED STATIONS INVENTORY (QC-WEBS SCRAPED)
            // ===============================================================
            Card {
                Layout.fillWidth: true
                implicitHeight: 220
                title: "Connected Wireless Client Stations"
                subtitle: "Real-time inventory scraped from embedded QC-Webs station_list.asp"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: (bridge?.wifiStations && bridge.wifiStations.length > 0)
                                ? (bridge.wifiStations.length + " station(s) associated with this softAP:")
                                : "No wireless client stations currently associated."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeBody
                            color: (bridge?.wifiStations && bridge.wifiStations.length > 0) ? Theme.colorCyan : Theme.textMuted
                        }

                        Item { Layout.fillWidth: true }

                        FelineButton {
                            text: "Refresh Stations"
                            variant: "outline"
                            iconGlyph: "⟳"
                            implicitHeight: 28
                            implicitWidth: 130
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.getWifiStations();
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.colorBorder
                    }

                    // Station List View
                    ListView {
                        id: stationList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: bridge?.wifiStations ?? []

                        delegate: Rectangle {
                            required property var modelData
                            width: stationList.width
                            height: 42
                            radius: Theme.radiusSm
                            color: (modelData.index % 2 === 0) ? Theme.colorObsidian : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spacingMd
                                anchors.rightMargin: Theme.spacingMd
                                spacing: Theme.spacingLg

                                Text {
                                    text: "#" + modelData.index
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textMuted
                                    width: 30
                                }

                                Text {
                                    text: modelData.mac
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: Theme.colorCyan
                                    width: 160
                                }

                                Text {
                                    text: modelData.hostname ? modelData.hostname : "Wireless Client"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textPrimary
                                }

                                Item { Layout.fillWidth: true }

                                StatusPill {
                                    label: "LINK"
                                    value: "ACTIVE"
                                    statusColor: Theme.colorSuccess
                                }
                            }
                        }

                        // Empty State Placeholder
                        Text {
                            anchors.centerIn: parent
                            visible: stationList.count === 0
                            text: "No external clients associated.\nConnect a phone, laptop, or auxiliary Wi-Fi dongle to inspect traffic."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.textMuted
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }
        }
    }
}
