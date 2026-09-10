import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."
import "../components"

Item {
    id: root

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
            // TOP STATUS & QUICK ACTION HERO BANNER
            // ===============================================================
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 96
                radius: Theme.radiusLg
                color: Theme.colorObsidian
                border.color: (bridge?.connected ?? false) ? Theme.colorBorderActive : Theme.colorBorder
                border.width: (bridge?.connected ?? false) ? 1.5 : 1

                Behavior on border.color { ColorAnimation { duration: Theme.animNormal } }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMd
                    spacing: Theme.spacingMd

                    // Connection Status Icon / Glow Tile
                    Rectangle {
                        width: 48
                        height: 48
                        radius: Theme.radiusMd
                        color: (bridge?.connected ?? false) ? Qt.rgba(0, 240, 255, 0.12) : Qt.rgba(255, 51, 102, 0.12)
                        border.color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.colorDanger
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: (bridge?.connected ?? false) ? "⚡" : "✕"
                            font.pixelSize: 22
                            color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.colorDanger
                        }
                    }

                    // Operator, RAT & Connection State
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSm

                            Text {
                                text: (bridge?.operator && bridge.operator.length > 0) ? bridge.operator : "Searching Carrier..."
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeH2
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }

                            // Technology Badge
                            Rectangle {
                                height: 20
                                width: techText.implicitWidth + 12
                                radius: Theme.radiusSm
                                color: Qt.rgba(243, 156, 18, 0.15)
                                border.color: Theme.colorGold
                                border.width: 1

                                Text {
                                    id: techText
                                    anchors.centerIn: parent
                                    text: (bridge?.technology && bridge.technology.length > 0) ? bridge.technology : "4G LTE"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    font.weight: Font.Bold
                                    color: Theme.colorGold
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSm

                            Text {
                                text: {
                                    if (bridge?.connecting ?? false) return "Connecting cellular data session (ppp0)...";
                                    if (bridge?.connected ?? false) return "Active cellular data plane linked to primary route (ppp0)";
                                    return "Qualcomm MDM9600 cellular radio registered and standing by";
                                }
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeCaption
                                color: (bridge?.connected ?? false) ? Theme.colorSuccess : Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            // IP Address Pill (if connected)
                            Rectangle {
                                visible: (bridge?.connected ?? false) && (bridge?.ipAddress && bridge.ipAddress.length > 0)
                                height: 18
                                width: ipText.implicitWidth + 10
                                radius: Theme.radiusSm
                                color: Qt.rgba(0, 240, 255, 0.12)
                                border.color: Qt.rgba(0, 240, 255, 0.4)
                                border.width: 1

                                Text {
                                    id: ipText
                                    anchors.centerIn: parent
                                    text: "IP: " + (bridge?.ipAddress ?? "")
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSmall
                                    font.weight: Font.Bold
                                    color: Theme.colorCyan
                                }
                            }
                        }
                    }

                    // Primary 1-Click Connect / Disconnect Button
                    FelineButton {
                        text: {
                            if (bridge?.connecting ?? false) return "Connecting...";
                            if (bridge?.connected ?? false) return "Disconnect";
                            return "Connect Cellular";
                        }
                        variant: (bridge?.connected ?? false) ? "danger" : "primary"
                        iconGlyph: (bridge?.connected ?? false) ? "⏹" : "▶"
                        loading: bridge?.connecting ?? false
                        implicitWidth: 142
                        implicitHeight: 42
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                if (bridge.connected) {
                                    bridge.disconnectData();
                                } else {
                                    bridge.connectData("internet");
                                }
                            }
                        }
                    }
                }
            }

            // ===============================================================
            // MIDDLE GRID: TELEMETRY & LIVE THROUGHPUT
            // ===============================================================
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: Theme.spacingMd
                columnSpacing: Theme.spacingMd

                // -----------------------------------------------------------
                // CARD 1: CELLULAR SIGNAL & RF QUALITY
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: "Cellular RF Telemetry"
                    subtitle: "Qualcomm MDM9600 Transceiver Quality"

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        // Big Signal Meter Display
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingLg

                            SignalBars {
                                bars: bridge?.signalBars ?? 0
                                csq: bridge?.signalCsq ?? 0
                                dbm: bridge?.signalDbm ?? -113
                                showText: false
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: (bridge?.signalBars ?? 0) + " of 5 Signal Bars"
                                    font.family: Theme.fontSans
                                    font.pixelSize: Theme.fontSizeH2
                                    font.weight: Font.Bold
                                    color: Theme.signalColor(bridge?.signalCsq ?? 0)
                                }

                                Text {
                                    text: Theme.csqToDbm(bridge?.signalCsq ?? 0) + " (" + (bridge?.signalCsq ?? 0) + "/31 CSQ)"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeCaption
                                    color: Theme.textSecondary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                        }

                        // Detailed Network Parameters Grid
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: Theme.spacingSm
                            columnSpacing: Theme.spacingMd

                            ColumnLayout {
                                spacing: 2
                                Text { text: "UPTIME"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                                Text {
                                    text: Theme.durationString(bridge?.sessionDuration ?? 0)
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text { text: "PEER GATEWAY"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                                Text {
                                    text: (bridge?.peerIp && bridge.peerIp.length > 0) ? bridge.peerIp : "—"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    font.weight: Font.Bold
                                    color: (bridge?.connected ?? false) ? Theme.colorCyan : Theme.textSecondary
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text { text: "PRIMARY DNS"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                                Text {
                                    text: (bridge?.dnsServers && bridge.dnsServers.length > 0) ? bridge.dnsServers[0] : "—"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textSecondary
                                }
                            }

                            ColumnLayout {
                                spacing: 2
                                Text { text: "SECONDARY DNS"; font.pixelSize: Theme.fontSizeSmall; font.family: Theme.fontMono; color: Theme.textMuted }
                                Text {
                                    text: (bridge?.dnsServers && bridge.dnsServers.length > 1) ? bridge.dnsServers[1] : "—"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeBody
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 2: REAL-TIME TRAFFIC THROUGHPUT
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: "Live Bandwidth & Throughput"
                    subtitle: "Real-time packet speedometers"

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        // Download Visualizer
                        BandwidthGraph {
                            Layout.fillWidth: true
                            title: "Download"
                            iconGlyph: "↓"
                            barColor: Theme.colorSuccess
                            history: bridge?.trafficHistoryRx ?? []
                            currentRateStr: Theme.formatRate(bridge?.rxRate ?? 0.0)
                            peakRateStr: Theme.formatRate(bridge?.peakRxRate ?? 0.0)
                            totalBytesStr: Theme.formatBytes(bridge?.rxBytes ?? 0)
                        }

                        // Upload Visualizer
                        BandwidthGraph {
                            Layout.fillWidth: true
                            title: "Upload"
                            iconGlyph: "↑"
                            barColor: Theme.colorCyan
                            history: bridge?.trafficHistoryTx ?? []
                            currentRateStr: Theme.formatRate(bridge?.txRate ?? 0.0)
                            peakRateStr: Theme.formatRate(bridge?.peakTxRate ?? 0.0)
                            totalBytesStr: Theme.formatBytes(bridge?.txBytes ?? 0)
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.colorBorder
                        }

                        // Cumulative Session Transfer
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSm

                            Text {
                                text: "Total Transferred: " + Theme.formatBytes((bridge?.rxBytes ?? 0) + (bridge?.txBytes ?? 0))
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeCaption
                                font.weight: Font.Bold
                                color: Theme.colorGold
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "Interface: ppp0"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textMuted
                            }
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 3: WI-FI HOTSPOT QUICK CONTROLS
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: "Wi-Fi Hotspot Co-Processor"
                    subtitle: "Broadcom 802.11b/g/n Subsystem"

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingLg

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: (bridge?.wifiPower ?? false) ? ("SSID: " + ((bridge?.wifiSsid && bridge.wifiSsid.length > 0) ? bridge.wifiSsid : "Active")) : "Wi-Fi Radio Disabled"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeH3
                                font.weight: Font.Bold
                                color: (bridge?.wifiPower ?? false) ? Theme.textPrimary : Theme.textMuted
                            }

                            Text {
                                text: (bridge?.wifiPower ?? false) ? ((bridge?.wifiClientsCount ?? 0) + " client(s) connected • SoftAP channel 11") : "Turn on Wi-Fi radio to broadcast wireless SSID"
                                font.family: Theme.fontSans
                                font.pixelSize: Theme.fontSizeCaption
                                color: Theme.textSecondary
                            }
                        }

                        FelineButton {
                            text: (bridge?.wifiPower ?? false) ? "Disable Wi-Fi" : "Enable Wi-Fi"
                            variant: (bridge?.wifiPower ?? false) ? "secondary" : "gold"
                            iconGlyph: "📶"
                            onClicked: {
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.toggleWifi();
                                }
                            }
                        }
                    }
                }

                // -----------------------------------------------------------
                // CARD 4: SYSTEM & ARCHITECTURE ENVIRONMENT
                // -----------------------------------------------------------
                Card {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    title: "System Architecture & IPC Binding"
                    subtitle: "Process communication and peripheral endpoints"

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "DAEMON STATUS:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: (bridge?.isDaemonRunning ?? false) ? "ONLINE (Active System Daemon)" : "DIRECT SERIAL FALLBACK"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                font.weight: Font.Bold
                                color: (bridge?.isDaemonRunning ?? false) ? Theme.colorSuccess : Theme.colorWarning
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "IPC TRANSPORT:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: (bridge?.transportMode ? bridge.transportMode.toUpperCase() : "SOCKET")
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                font.weight: Font.Bold
                                color: Theme.colorCyan
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "HARDWARE TARGET:"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSmall; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: "Qualcomm MDM9600 (Aleka UV310)"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.textSecondary
                            }
                        }
                    }
                }
            }
        }
    }
}
