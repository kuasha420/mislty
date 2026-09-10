import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

    property bool showPassword: false
    property bool showRelayPassword: false

    ScrollView {
        id: scroll
        objectName: "wifiScrollView"
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
            // ASSIST WI-FI HOTSPOT RELAY (SIMULTANEOUS 4G WAN + SOFTAP)
            // ===============================================================
            Card {
                Layout.fillWidth: true
                title: "Assist Wi-Fi Hotspot Relay (Simultaneous 4G WAN + SoftAP)"
                subtitle: "Broadcast an independent Wi-Fi hotspot on auxiliary WLAN hardware (e.g. TP-Link USB adapter), sharing 4G LTE cellular data over ppp0 without touching host connection."

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    // Top Status Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        StatusPill {
                            label: "RELAY"
                            value: (bridge?.relayActive ?? false) ? "ACTIVE" : "STANDBY"
                            statusColor: (bridge?.relayActive ?? false) ? Theme.colorSuccess : Theme.textMuted
                        }

                        StatusPill {
                            label: "DEVICE"
                            value: (bridge?.relayInterface && bridge.relayInterface.length > 0) ? bridge.relayInterface : "None"
                            statusColor: Theme.colorCyan
                        }

                        StatusPill {
                            label: "SUBNET"
                            value: (bridge?.relayIpAddress && bridge.relayIpAddress.length > 0) ? (bridge.relayIpAddress + "/24") : "10.42.0.1/24"
                            statusColor: Theme.colorGold
                        }

                        StatusPill {
                            label: "WAN"
                            value: (bridge?.relayWanInterface && bridge.relayWanInterface.length > 0) ? bridge.relayWanInterface : "ppp0"
                            statusColor: Theme.colorPurple
                        }

                        Item { Layout.fillWidth: true }

                        FelineButton {
                            text: "Scan Adapters"
                            variant: "outline"
                            iconGlyph: "🔍"
                            implicitHeight: 28
                            implicitWidth: 125
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.refreshWlanDevices();
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.colorBorder
                    }

                    // Device & Network Configuration Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        // Adapter Selector
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 260
                            spacing: Theme.spacingXs

                            Text {
                                text: "ASSIST WLAN ADAPTER (PROTECTS PRIMARY)"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textSecondary
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                ComboBox {
                                    id: relayDeviceBox
                                    anchors.fill: parent
                                    enabled: !(bridge?.relayActive ?? false)
                                    model: {
                                        var devs = bridge?.wlanDevices ?? [];
                                        var labels = [];
                                        for (var i = 0; i < devs.length; i++) {
                                            var d = devs[i];
                                            var tag = d.is_primary ? " [Protected Host]" : (d.is_candidate ? " [Candidate AP]" : " [Unsupported]");
                                            var name = d.iface + " (" + (d.vendor ? d.vendor + " " : "") + (d.model ? d.model : d.driver) + ")" + tag;
                                            labels.push(name);
                                        }
                                        return labels.length > 0 ? labels : ["No WLAN adapters detected"];
                                    }
                                    currentIndex: {
                                        var devs = bridge?.wlanDevices ?? [];
                                        for (var i = 0; i < devs.length; i++) {
                                            if (devs[i].is_candidate) return i;
                                        }
                                        return 0;
                                    }
                                    background: Rectangle { color: "transparent" }
                                    contentItem: TextEdit {
                                        readOnly: true
                                        selectByMouse: false
                                        leftPadding: 10
                                        text: relayDeviceBox.displayText
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textPrimary
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        // Hotspot SSID Input
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Text {
                                text: "HOTSPOT SSID (BROADCAST NAME)"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textSecondary
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                TextInput {
                                    id: relaySsidInput
                                    anchors.fill: parent
                                    anchors.margins: Theme.spacingSm
                                    enabled: !(bridge?.relayActive ?? false)
                                    text: (bridge?.relaySsid && bridge.relaySsid.length > 0) ? bridge.relaySsid : "MisLTy 4G Share"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textPrimary
                                    selectByMouse: true
                                }
                            }
                        }

                        // WPA2-PSK Passphrase Input
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Text {
                                text: "WPA2-PSK PASSPHRASE"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textSecondary
                            }

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
                                        id: relayPassInput
                                        Layout.fillWidth: true
                                        enabled: !(bridge?.relayActive ?? false)
                                        text: "mislty420"
                                        echoMode: root.showRelayPassword ? TextInput.Normal : TextInput.Password
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeBody
                                        color: Theme.textPrimary
                                        selectByMouse: true
                                    }

                                    Text {
                                        text: root.showRelayPassword ? "🙈" : "👁"
                                        font.pixelSize: 16
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.showRelayPassword = !root.showRelayPassword
                                        }
                                    }
                                }
                            }
                        }

                        // Band & Channel Selector
                        ColumnLayout {
                            Layout.preferredWidth: 150
                            spacing: Theme.spacingXs

                            Text {
                                text: "BAND / CHANNEL"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textSecondary
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.colorObsidian
                                border.color: Theme.colorBorder
                                border.width: 1

                                ComboBox {
                                    id: relayChannelBox
                                    anchors.fill: parent
                                    enabled: !(bridge?.relayActive ?? false)
                                    model: ["Ch 11 (2.4 GHz)", "Ch 6 (2.4 GHz)", "Ch 1 (2.4 GHz)", "Ch 36 (5 GHz)", "Ch 149 (5 GHz)"]
                                    currentIndex: 0
                                    background: Rectangle { color: "transparent" }
                                    contentItem: TextEdit {
                                        readOnly: true
                                        selectByMouse: false
                                        leftPadding: 10
                                        text: relayChannelBox.displayText
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textPrimary
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                    }

                    // Action Controls & Status Bar
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        FelineButton {
                            text: (bridge?.relayActive ?? false) ? "Stop Hotspot Relay" : "Start Hotspot Relay"
                            variant: (bridge?.relayActive ?? false) ? "danger" : "primary"
                            iconGlyph: (bridge?.relayActive ?? false) ? "🛑" : "📡"
                            implicitWidth: 180
                            implicitHeight: 38
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    if (bridge.relayActive) {
                                        bridge.stopHotspotRelay();
                                    } else {
                                        var devs = bridge.wlanDevices ?? [];
                                        var targetIface = "wlan1";
                                        if (devs.length > relayDeviceBox.currentIndex) {
                                            targetIface = devs[relayDeviceBox.currentIndex].iface;
                                        }
                                        var band = "bg";
                                        var ch = 11;
                                        if (relayChannelBox.currentIndex === 1) { ch = 6; band = "bg"; }
                                        else if (relayChannelBox.currentIndex === 2) { ch = 1; band = "bg"; }
                                        else if (relayChannelBox.currentIndex === 3) { ch = 36; band = "a"; }
                                        else if (relayChannelBox.currentIndex === 4) { ch = 149; band = "a"; }

                                        bridge.startHotspotRelay(
                                            targetIface,
                                            relaySsidInput.text,
                                            relayPassInput.text,
                                            band,
                                            ch,
                                            "ppp0"
                                        );
                                    }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (bridge?.relayActive ?? false)
                                ? ("● Broadcasting on " + (bridge?.relayInterface ?? "wlan1") + " (" + (bridge?.relaySsid ?? "") + ") • Gateway: " + (bridge?.relayIpAddress ?? "10.42.0.1") + " • Upstream WAN: " + (bridge?.relayWanInterface ?? "ppp0") + " (LTE)")
                                : "Auxiliary adapter ready. Click 'Start Hotspot Relay' to broadcast Wi-Fi softAP and forward client traffic out 4G modem."
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            color: (bridge?.relayActive ?? false) ? Theme.colorSuccess : Theme.textMuted
                            elide: Text.ElideRight
                        }

                        FelineButton {
                            text: "Refresh Clients"
                            variant: "outline"
                            iconGlyph: "⟳"
                            implicitHeight: 34
                            implicitWidth: 130
                            visible: (bridge?.relayActive ?? false)
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.getHotspotRelayClients();
                                }
                            }
                        }
                    }

                    // Connected Relay Stations Table
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingXs
                        visible: (bridge?.relayActive ?? false)

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                        }

                        Text {
                            text: "CONNECTED RELAY STATIONS (" + (bridge?.relayClients?.length ?? 0) + ")"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSmall
                            font.weight: Font.Bold
                            color: Theme.colorCyan
                        }

                        ListView {
                            id: relayStationList
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(70, Math.min(240, (bridge?.relayClients?.length ?? 0) * 44))
                            clip: true
                            model: bridge?.relayClients ?? []

                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                width: relayStationList.width
                                height: 40
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
                                        width: 25
                                    }

                                    Text {
                                        text: modelData.mac
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeBody
                                        font.weight: Font.Bold
                                        color: Theme.colorCyan
                                        width: 150
                                    }

                                    Text {
                                        text: modelData.ip ? modelData.ip : "Assigning IP..."
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeBody
                                        color: modelData.ip ? Theme.colorSuccess : Theme.textMuted
                                        width: 140
                                    }

                                    Text {
                                        text: (modelData.signal_dbm !== null && modelData.signal_dbm !== undefined) ? (modelData.signal_dbm + " dBm") : "Signal N/A"
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSmall
                                        color: Theme.textSecondary
                                        width: 90
                                    }

                                    Item { Layout.fillWidth: true }

                                    StatusPill {
                                        label: "FORWARDING"
                                        value: "PPP0 WAN"
                                        statusColor: Theme.colorPurple
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: relayStationList.count === 0
                                text: "No client devices connected to relay hotspot yet.\nConnect phones, tablets, or laptops to " + (bridge?.relaySsid ?? "the hotspot") + "."
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textMuted
                                horizontalAlignment: Text.AlignHCenter
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
                        Layout.preferredHeight: Math.max(90, Math.min(240, (bridge?.wifiStations?.length ?? 0) * 44))
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
