import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property bool showPassword: false

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        rightPadding: 16
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            width: scroll.availableWidth
            spacing: Theme.spacingMd

            // ===============================================================
            // TOP HERO CARD: WI-FI RADIO CONTROLLER & DUAL-PLANE STATE
            // ===============================================================
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 96
                radius: Theme.radiusLg
                color: Theme.colorObsidian
                border.color: (bridge?.wifiPower ?? false) ? Theme.colorBorderActive : Theme.colorBorder
                border.width: (bridge?.wifiPower ?? false) ? 1.5 : 1

                Behavior on border.color { ColorAnimation { duration: Theme.animNormal } }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: Theme.spacingMd

                    // Radio Icon Tile
                    Rectangle {
                        width: 48
                        height: 48
                        radius: Theme.radiusMd
                        color: (bridge?.wifiPower ?? false) ? Qt.rgba(0, 240, 255, 0.12) : Qt.rgba(121, 130, 169, 0.12)
                        border.color: (bridge?.wifiPower ?? false) ? Theme.colorCyan : Theme.colorBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: (bridge?.wifiPower ?? false) ? "📶" : "💤"
                            font.pixelSize: 22
                        }
                    }

                    // Radio Metadata
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSm

                            Text {
                                text: (bridge?.wifiPower ?? false) ? "Wi-Fi Hotspot: ACTIVE" : "Wi-Fi Hotspot: STANDBY"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeH2
                                font.weight: Font.Bold
                                color: (bridge?.wifiPower ?? false) ? Theme.colorSuccess : Theme.textMuted
                                elide: Text.ElideRight
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

                            Item { Layout.fillWidth: true }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (bridge?.wifiPower ?? false)
                                ? ("Broadcom 802.11b/g/n • SSID '" + ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "Active") + "' • Channel 11")
                                : "Radio powered down into low-power sleep mode (commit to NVRAM)."
                            font.family: Theme.fontSans
                            font.pixelSize: Theme.fontSizeCaption
                            color: Theme.textSecondary
                            elide: Text.ElideRight
                        }
                    }

                    // Radio Power Toggle Action
                    FelineButton {
                        text: (bridge?.wifiPower ?? false) ? "Disable Hotspot" : "Enable Hotspot"
                        variant: (bridge?.wifiPower ?? false) ? "danger" : "gold"
                        iconGlyph: "⚡"
                        implicitWidth: 145
                        implicitHeight: 40
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
                    Layout.fillWidth: true
                    spacing: Theme.spacingLg

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
                                    text: "Host direct ppp0 dialup • Native kernel network interface • Full Linux desktop routing"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeSmall
                                    color: Theme.textSecondary
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
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
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
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
                    Layout.fillWidth: true
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
                            Layout.preferredWidth: 140
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
                                    model: ["Ch 11 (2.462 GHz)", "Ch 6 (2.437 GHz)", "Ch 1 (2.412 GHz)", "Auto (Adaptive)"]
                                    currentIndex: 0
                                    background: Rectangle { color: "transparent" }
                                    contentItem: TextEdit {
                                        readOnly: true
                                        selectByMouse: false
                                        leftPadding: 10
                                        text: channelBox.displayText
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textPrimary
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                    }

                    // Save / Apply Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        FelineButton {
                            text: "Open Web UI"
                            variant: "outline"
                            iconGlyph: "🌐"
                            implicitHeight: 38
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.openWebUi();
                                }
                            }
                        }

                        FelineButton {
                            text: "Reboot Modem"
                            variant: "secondary"
                            iconGlyph: "🔄"
                            implicitHeight: 38
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
                            implicitWidth: 150
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
                title: "Connected Wireless Client Stations"
                subtitle: "Real-time inventory scraped from embedded QC-Webs station_list.asp"

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
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
                        implicitHeight: Math.max(90, Math.min(240, (bridge?.wifiStations?.length ?? 0) * 44))
                        clip: true
                        model: bridge?.wifiStations ?? []

                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: stationList.width
                            height: 42
                            radius: Theme.radiusSm
                            color: (index % 2 === 0) ? Theme.colorObsidian : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spacingMd
                                anchors.rightMargin: Theme.spacingMd
                                spacing: Theme.spacingLg

                                Text {
                                    text: "#" + (index + 1)
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
